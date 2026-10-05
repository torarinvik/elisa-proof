#!/usr/bin/env python3
"""Build the real Elisa profiler with fresh Stage1 and test runtime lifetimes."""

from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
from collections import Counter


ROOT = Path(__file__).resolve().parents[2]
PROFILER_ROOT = ROOT.parent / "elisa-profiler"
COMPILER_ROOT = ROOT.parent / "Elisa-compiler"
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
RUNTIME = COMPILER_ROOT / "build" / "runtime" / "elisacore_runtime.o"
PROBE = ROOT / "examples" / "proof_allocation_lifetime.elisa"
POST_RESET_VIEW_NEGATIVE = ROOT / "examples" / "rejected_sview_after_region_destroy.elisa"
PROOF_BIN = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build" / "elisa-proof"))


def run(command: list[str], *, env: dict[str, str], timeout: int = 900) -> str:
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=timeout, check=False)
    if completed.returncode:
        raise AssertionError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout[-12000:]}"
        )
    return completed.stdout


def main() -> None:
    if not STAGE1.is_file() or not RUNTIME.is_file():
        raise SystemExit("R-014 requires the compiler checkout's Stage1 and matching runtime")
    if not PROOF_BIN.is_file():
        raise SystemExit("R-014 post-reset sview control requires ELISA_PROOF_BIN or build/elisa-proof")

    env = os.environ.copy()
    env.update({
        "ELISA_COMPILER_ROOT": str(COMPILER_ROOT),
        "ELISA_STAGE1_BIN": str(STAGE1),
        "ELISA_RUNTIME_OBJ": str(RUNTIME),
        "ELISA_PROFILER_RUNTIME_C": str(PROFILER_ROOT / "scripts" / "profiler_runtime.c"),
        "ELISA_STAGE1_MAX_RSS_KB": env.get("ELISA_STAGE1_MAX_RSS_KB", "8388608"),
    })
    run(["python3", str(COMPILER_ROOT / "scripts" / "stage1_provenance.py"),
         "check", str(COMPILER_ROOT), str(STAGE1)], env=env, timeout=30)

    # This is a verifier-side safety control, not a runtime dereference of stale
    # storage. The valid runtime probe below separately reads its view before
    # destroying the backing region.
    negative = subprocess.run(
        [str(PROOF_BIN), "--json", str(POST_RESET_VIEW_NEGATIVE)],
        cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=900, check=False,
    )
    assert negative.returncode == 1, (
        f"post-reset sview control was not refused (exit {negative.returncode}):\n"
        f"{negative.stdout[-12000:]}"
    )
    negative_report = json.loads(negative.stdout)
    assert negative_report["status"] == "failed", negative_report.get("status")
    assert any(finding["kind"] in {
        "region-use-after-destroy", "region-destroy-live-borrow"
    } for finding in negative_report.get("findings", [])), negative_report.get("findings")
    assert negative_report["replay"]["gaps"] == 0, negative_report["replay"]

    with tempfile.TemporaryDirectory(prefix="elisa-r014-profiler-") as temporary:
        work = Path(temporary)
        profiler = work / "elisa-profiler"
        run(["bash", str(PROFILER_ROOT / "scripts" / "build-native.sh"),
             str(COMPILER_ROOT / "scripts" / "elisac_stage1.sh"), str(STAGE1),
             str(COMPILER_ROOT), str(RUNTIME), "O2", str(profiler)],
            env=env, timeout=900)

        capture_path = work / "capture.json"
        env["TMPDIR"] = str(work)
        run([str(profiler), "profile", str(PROBE), "--mode", "full",
             "--format", "json", "--output", str(capture_path),
             "--no-cache", "--warmup", "0", "--repeat", "1", "--timeout", "120"],
            env=env, timeout=900)

        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        execution = capture["run"]
        assert execution["outcome"] == "success", execution["outcome"]
        assert execution["exit_code"] == 0, execution["exit_code"]
        assert capture["summary"]["capture_complete"] is True
        repetition, = execution["repetitions"]
        assert repetition["capture_complete"] is True
        assert repetition["timed_out"] is False
        assert repetition.get("allocation_events_dropped", 0) == 0
        assert repetition["allocation_hook_abi"] == {
            "negotiated_v1": True,
            "legacy_calls": False,
            "rejected_version": False,
            "v1_calls": True,
        }

        events = sorted(repetition["allocation_events"], key=lambda event: event["sequence"])
        assert repetition["region_layouts"], "no actual runtime region-layout hook evidence"
        alloc32 = [event for event in events
                   if event["kind"] == "alloc" and event["size_bytes"] == 32]
        alloc64 = [event for event in events
                   if event["kind"] == "alloc" and event["size_bytes"] == 64]
        reclaim32 = [event for event in events
                     if event["kind"] == "reclaim" and event["old_size_bytes"] == 32]
        assert alloc32 and alloc64 and reclaim32, "known requested-size lifecycle events missing"

        # The reclaim callback identifies the exact 32-byte span. Its reuse as 16
        # bytes and the explicit reset must occur on the same arena in sequence.
        reclaimed, = reclaim32
        original = [event for event in alloc32
                    if event["address"] == reclaimed["old_address"]
                    and event["arena"] == reclaimed["arena"]
                    and event["sequence"] < reclaimed["sequence"]]
        assert original, "reclaim did not correspond to the known 32-byte allocation"
        reused = [event for event in events
                  if event["kind"] == "alloc" and event["size_bytes"] == 16
                  and event["address"] == reclaimed["old_address"]
                  and event["arena"] == reclaimed["arena"]
                  and event["sequence"] > reclaimed["sequence"]]
        assert reused, "the reclaimed span was not observed reused at the expected address"
        resets = [event for event in events
                  if event["kind"] == "region_reset"
                  and event["arena"] == reclaimed["arena"]
                  and event["sequence"] > reused[0]["sequence"]]
        assert resets, "the explicit arena reset was not observed after reuse"

        # Analyze the unmodified runtime capture with the profiler's production
        # lifecycle reconciler. It must preserve separate logical/capacity metrics.
        analyzer_path = PROFILER_ROOT / "scripts" / "analyze-allocation-sites.py"
        analyzer_spec = importlib.util.spec_from_file_location("allocation_lifetime_analyzer", analyzer_path)
        assert analyzer_spec is not None and analyzer_spec.loader is not None
        analyzer = importlib.util.module_from_spec(analyzer_spec)
        analyzer_spec.loader.exec_module(analyzer)
        analysis = analyzer.analyze(capture)["repetitions"][0]
        assert analysis["lifetime_status"] == "available", analysis["lifetime_reason"]
        metrics = analysis["metrics"]
        assert metrics["peak_logical_live_bytes"] >= 64
        assert metrics["peak_observed_backing_capacity_bytes"] >= metrics["peak_logical_live_bytes"]
        assert metrics["logical_live_bytes_at_capture_end"] == 0
        assert metrics["observed_backing_capacity_at_capture_end_bytes"] == 0
        assert metrics["max_retained_backing_capacity_after_reset_bytes"] > 0
        assert "peak_rss_bytes" in repetition  # independent OS observation, may be null
        assert repetition["peak_rss_bytes"] is None or repetition["peak_rss_bytes"] > 0

        print("R-014 real profiler runtime-lifetime probe OK")
        print("  post-reset sview control: verifier refusal, zero replay gaps")
        print(f"  runtime event kinds: {dict(sorted(Counter(e['kind'] for e in events).items()))}")
        print("  explicit workload: alloc 32, alloc 64, reclaim 32, reuse 16, region reset")
        print(f"  peak logical live bytes: {metrics['peak_logical_live_bytes']}")
        print(f"  logical live bytes at capture end: {metrics['logical_live_bytes_at_capture_end']}")
        print(f"  peak observed backing capacity: {metrics['peak_observed_backing_capacity_bytes']}")
        print(f"  backing capacity at capture end: {metrics['observed_backing_capacity_at_capture_end_bytes']}")
        print(f"  max retained capacity after reset: {metrics['max_retained_backing_capacity_after_reset_bytes']}")
        print(f"  observed reuse boundaries: {metrics['observed_reuses']}")
        print(f"  peak RSS: {repetition['peak_rss_bytes']!r} (independent OS metric)")
        print("  instrumentation overhead: unavailable (no matched uninstrumented baseline)")


if __name__ == "__main__":
    main()
