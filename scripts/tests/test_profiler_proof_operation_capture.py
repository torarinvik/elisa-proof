"""Pinned end-to-end check that profiling preserves a complete proof result.

This is a semantic capture-calibration, not an overhead benchmark. Every input product is
identity-checked, captures must report zero loss, and every report field except instrumentation
measurements must match an uninstrumented run of the exact same proof executable.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PROFILER_SHA256 = "eb4e06d91e737abb87aedd7a1b2d280218ed1036033d609bc729befbb32f4101"
PROFILER_REVISION = "39f46e4983c4e233b542e7c57ff27f15c96fb8e2"
STAGE1_SHA256 = "1bf9bf4e1301c56c25bedb079e385f2fdd80e243a992a95bcfd3da6b41a059a3"
COMPILER_REVISION = "a3532bd93eba8d2cd81fb9f609b03a636f087a23"
RUNTIME_SHA256 = "6b801abede4f9d601bc0da773e16afd194f6bb11ed0308619aff70be98a2355c"
PROOF_SOURCE_TREE_SHA256 = "5f94713e92fe0bb30fa9cd4998c477515d7bc2e933069bcd5881b0f1a969fbc5"
PROOF_MAIN_SHA256 = "c6d7d932bc3af6748848e2bcd3c1ab49bbcd0535d450216df2ebacd52aaaad9f"
PRODUCER_SHA256 = "0d43e1ebede14dbd1f50b8d1ceb745b46588d51fd535d3a92dba8a528fdb051a"
PRODUCER_BUILD_ID = "15b334c086d32f3d39f1d25d63440ff5f1ed857d92640c97962d0bc21c3cd29b"
REPLAY_SHA256 = "6f67b9259c10f8f8653c4e68862140b8a9d1f502d4b2e83dcb33b143b2966f70"
REPLAY_BUILD_ID = "c9fa24278df7b48b954ef89f059b1944cb98a8139ee330c55b2663d9b50f406d"
WORKLOAD = Path("examples/verified.elisa")
WORKLOAD_SHA256 = "cd0b15fb9d6334269ab777674568ee0719035fd02ceeaa3decfa448be716458f"
LOSS_COUNTERS = (
    "dropped", "allocation_events_dropped", "frame_dropped", "capture_bytes_dropped",
    "dropped_call_edges", "dropped_stacks", "stack_overflow_entries", "trace_events_omitted",
)
REPETITION_LOSS_FIELDS = {
    "trace_dropped": "dropped",
    "allocation_events_dropped": "allocation_events_dropped",
    "frame_dropped": "frame_dropped",
    "capture_bytes_dropped": "capture_bytes_dropped",
    "dropped_call_edges": "dropped_call_edges",
    "dropped_stacks": "dropped_stacks",
    "trace_stack_overflow_entries": "stack_overflow_entries",
    "trace_events_omitted": "trace_events_omitted",
}
PHASE_COUNTERS = (
    "control_flow_steps", "live_facts_peak", "goal_cache_misses", "fact_traces",
    "kernel_nodes", "kernel_nodes_shared",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for directory, subdirectories, files in os.walk(root):
        subdirectories.sort()
        for name in sorted(files):
            path = Path(directory) / name
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    assert path.is_file(), f"missing {label}: {path}"
    actual = sha256(path)
    assert actual == expected, f"{label} hash mismatch: expected {expected}, got {actual}"


def compiler_source_revision(root: Path) -> str:
    snapshot = root / "SNAPSHOT"
    if snapshot.is_file():
        rows = [line.split(":", 1)[1].strip() for line in snapshot.read_text().splitlines()
                if line.startswith("source_revision:")]
        assert len(rows) == 1, f"invalid compiler snapshot provenance: {snapshot}"
        return rows[0]
    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                           capture_output=True, text=True, check=True).stdout.strip()
    assert not dirty, f"compiler checkout is dirty; revision {revision} is not a complete identity"
    return revision


def run(command: list[str], environment: dict[str, str], timeout: int = 1200):
    return subprocess.run(command, env=environment, capture_output=True, text=True,
                          check=False, timeout=timeout)


def semantic_projection(report: dict) -> dict:
    result = copy.deepcopy(report)
    result.pop("measurements")
    return result


def main() -> None:
    profiler = Path(os.environ["ELISA_PROFILER"]).resolve()
    compiler_root = Path(os.environ["ELISA_COMPILER_ROOT"]).resolve()
    compiler = compiler_root / "bin/elisac-stage1"
    runtime = compiler_root / "build/runtime/elisacore_runtime.o"
    producer = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof")).resolve()
    replay = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay")).resolve()
    workload = ROOT / WORKLOAD

    require_hash(profiler, PROFILER_SHA256, "elisa-profiler executable")
    profiler_revision = subprocess.run(
        ["git", "-C", str(profiler.parent.parent), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert profiler_revision == PROFILER_REVISION, profiler_revision
    require_hash(compiler, STAGE1_SHA256, "Stage1 compiler product")
    assert compiler_source_revision(compiler_root) == COMPILER_REVISION
    require_hash(runtime, RUNTIME_SHA256, "Stage1 runtime object")
    require_hash(workload, WORKLOAD_SHA256, "proof workload")
    require_hash(ROOT / "src/main.elisa", PROOF_MAIN_SHA256, "proof CLI source")
    assert source_tree_sha256(ROOT / "src") == PROOF_SOURCE_TREE_SHA256
    require_hash(producer, PRODUCER_SHA256, "baseline proof product")
    require_hash(replay, REPLAY_SHA256, "baseline replay product")

    producer_manifest = json.loads(Path(str(producer) + ".manifest.json").read_text())
    replay_manifest = json.loads(Path(str(replay) + ".manifest.json").read_text())
    assert producer_manifest["build_identity"] == PRODUCER_BUILD_ID
    assert replay_manifest["build_identity"] == REPLAY_BUILD_ID
    assert producer_manifest["proof"]["source_tree_sha256"] == PROOF_SOURCE_TREE_SHA256
    assert replay_manifest["proof"]["source_tree_sha256"] == PROOF_SOURCE_TREE_SHA256
    for key in ("revision",):
        assert producer_manifest["frontend"][key] == replay_manifest["frontend"][key]
    assert producer_manifest["frontend"]["revision"] == COMPILER_REVISION
    assert producer_manifest["compiler"]["product"]["sha256"] == STAGE1_SHA256
    assert replay_manifest["compiler"]["product"]["sha256"] == STAGE1_SHA256

    environment = os.environ.copy()
    environment.update({
        "ELISA_COMPILER_ROOT": str(compiler_root),
        "ELISA_COMPILER_REV": COMPILER_REVISION,
        "ELISA_STAGE1_BIN": str(compiler),
        "ELISA_COMPILER_BIN": str(compiler),
        "ELISA_RUNTIME_OBJ": str(runtime),
        "ELISA_COMPILER_SCRIPT": str(compiler_root / "scripts/elisac_stage1.sh"),
        "ELISA_PROFILER_TOOL_TIMEOUT_SECONDS": "1200",
        "ELISA_PROFILER_MAX_PROGRAM_OUTPUT_BYTES": "16777216",
    })

    with tempfile.TemporaryDirectory(prefix="elisa-proof-profiler-e2e-") as temporary:
        sandbox = Path(temporary)
        sandbox_proof = sandbox / "elisa-proof"
        shutil.copytree(ROOT / "src", sandbox_proof / "src")
        (sandbox_proof / "examples").mkdir()
        shutil.copyfile(workload, sandbox_proof / WORKLOAD)
        (sandbox / "Elisa-compiler").symlink_to(compiler_root, target_is_directory=True)
        profiled_workload = sandbox_proof / WORKLOAD
        capture_path = sandbox / "capture.json"
        instrumented_product = sandbox / "proof-instrumented"
        command = [
            str(profiler), "profile", str(sandbox_proof / "src/main.elisa"),
            "--mode", "functions", "--repeat", "1", "--warmup", "0",
            "--format", "json", "--output", str(capture_path),
            "--cache-dir", str(sandbox / "cache"),
            "--artifact-output", str(instrumented_product), "--",
            "--json", str(profiled_workload),
        ]
        captured = run(command, environment)
        assert captured.returncode == 0, (captured.returncode, captured.stdout, captured.stderr)
        assert capture_path.is_file() and instrumented_product.is_file()
        capture = json.loads(capture_path.read_text())
        assert capture["compiler"]["stage1_sha256"] == STAGE1_SHA256
        assert capture["compiler"]["runtime_object_sha256"] == RUNTIME_SHA256
        assert capture["run"]["collection_mode"] == "functions"
        assert capture["run"]["outcome"] == "success" and capture["run"]["exit_code"] == 0
        assert capture["run"]["requested_repetitions"] == 1
        assert capture["run"]["completed_repetitions"] == 1
        assert capture["run"]["successful_repetitions"] == 1
        assert capture["program_stdout_truncated"] is False
        summary = capture["summary"]
        assert summary["capture_started"] and summary["capture_complete"]
        assert not summary["detail_budget_exceeded"]
        for key in LOSS_COUNTERS:
            assert summary[key] == 0, (key, summary[key])
        repetition = capture["run"]["repetitions"][0]
        assert repetition["capture_started"] and repetition["capture_complete"]
        for field, summary_key in REPETITION_LOSS_FIELDS.items():
            assert repetition[field] == 0, (field, repetition[field])

        captured_report = json.loads(capture["program_stdout"])
        measurements = captured_report["measurements"]
        assert measurements["format"] == "elisa-proof-measurements-v1"
        for key in PHASE_COUNTERS:
            assert isinstance(measurements[key], int) and measurements[key] >= 0
        assert captured_report["status"] == "proved"
        assert captured_report["summary"]["proven"] == captured_report["summary"]["obligations"] > 0
        assert captured_report["replay"]["replayed"] == captured_report["replay"]["certificates"]
        assert captured_report["replay"]["gaps"] == 0
        assert captured_report["trust"]["trusted_assumptions"] == []

        baseline = run([str(producer), "--json", str(profiled_workload)], environment)
        assert baseline.returncode == 0, (baseline.returncode, baseline.stderr)
        baseline_report = json.loads(baseline.stdout)
        assert semantic_projection(captured_report) == semantic_projection(baseline_report), (
            "profiling changed proof semantics or report fields beyond measurements"
        )

        print(json.dumps({
            "result": "complete-loss-free-proof-capture",
            "profiler_revision": PROFILER_REVISION,
            "compiler_revision": COMPILER_REVISION,
            "stage1_sha256": STAGE1_SHA256,
            "proof_build_identity": PRODUCER_BUILD_ID,
            "proof_source_tree_sha256": PROOF_SOURCE_TREE_SHA256,
            "obligations": captured_report["summary"]["obligations"],
            "certificates_replayed": captured_report["replay"]["replayed"],
            "capture_events": summary["events"],
            "capture_bytes": summary["capture_bytes_used"],
            "semantic_projection_equal": True,
            "profiler_execution_ms": capture["run"]["execution_ms"],
        }, sort_keys=True))


if __name__ == "__main__":
    main()
