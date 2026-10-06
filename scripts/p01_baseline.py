#!/usr/bin/env python3
"""Bounded P-01 proof CLI baseline. Does not build, install, or alter repository files."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
from pathlib import Path

SCHEMA = "elisa-proof-p01-baseline-v4"
from p01_manifest import (
    EXPECTED_OUTCOMES, FIXTURES, MAX_OUTPUT_BYTES, ROOT, SENTINEL_MANIFEST, SHAPE_METRICS,
    build_identity, identity, load_sentinel_manifest, source_line_count,
    validate_probe_identity, validate_workload_identities,
)
from p01_measurements import check_report, invoke, shape_metrics

PHASE_TIMING_AVAILABILITY = {
    "proof_cli_invocation_wall": "measured-external-monotonic-wall",
    "proof_cli_child_cpu": "measured-wait4-child-user-plus-system",
    "baseline_harness_json_decode": "measured-external-monotonic-wall",
    "source_import_expansion": "unavailable-no-internal-clock-hook",
    "lexing": "unavailable-no-internal-clock-hook",
    "parsing": "unavailable-no-internal-clock-hook",
    "resolution_and_semantics": "unavailable-single-opaque-semantic-api-call",
    "summary_scheduling": "unavailable-no-internal-clock-hook",
    "verification_condition_generation": "unavailable-interleaved-with-proof-search",
    "proof_search": "unavailable-interleaved-with-goal-recording",
    "certificate_encoding": "unavailable-shared-encoder-calls-not-timed",
    "kernel_replay": "unavailable-no-internal-clock-hook",
    "proof_json_reporting": "unavailable-no-internal-clock-hook",
}
def summarize(rows: list[dict]) -> dict:
    times = [row["wall_seconds"] for row in rows]
    cpu_times = [row["cpu_seconds"] for row in rows if row.get("cpu_seconds") is not None]
    return {"runs": len(rows), "median_wall_seconds": statistics.median(times),
            "p95_wall_seconds": sorted(times)[max(0, (95 * len(times) + 99) // 100 - 1)],
            "median_cpu_seconds": statistics.median(cpu_times) if cpu_times else None,
            "p95_cpu_seconds": sorted(cpu_times)[max(0, (95 * len(cpu_times) + 99) // 100 - 1)]
                if cpu_times else None,
            "max_peak_rss_kib": max(row["peak_rss_kib"] for row in rows)}


def run(args: argparse.Namespace) -> dict:
    binary = args.binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(f"proof binary is not executable: {binary}")
    build = build_identity(binary)
    if not build.get("available"):
        raise RuntimeError(f"P-01 requires a verified build manifest: {build.get('reason')}")
    replay_binary = ROOT / "build" / "elisa-proof-replay"
    replay_build = build_identity(replay_binary)
    if not replay_build.get("available"):
        raise RuntimeError(f"P-01 requires a verified standalone replay manifest: {replay_build.get('reason')}")
    rounds = getattr(args, "rounds", 1)
    warmup_runs = getattr(args, "warmup_runs", 0)
    if rounds <= 0 or warmup_runs < 0:
        raise RuntimeError("rounds must be positive and warm-up runs cannot be negative")
    sentinels = load_sentinel_manifest()
    sentinel_payload = json.loads(SENTINEL_MANIFEST.read_text(encoding="utf-8"))
    validate_probe_identity(sentinel_payload["semantic_probe"], build, binary,
                            replay_build, replay_binary)
    fixture_ids = validate_workload_identities(sentinels)
    manifest = sentinel_payload
    for workload_name, workload in manifest.get("workloads", {}).items():
        members = workload.get("members", [])
        if not any(member in sentinels for member in members):
            continue
        if any(member not in sentinels for member in members):
            raise RuntimeError(f"P-01 workload {workload_name} names a non-pinned fixture")
        for member in members:
            if sentinels[member].get("workload") != workload_name:
                raise RuntimeError(f"P-01 fixture {member} is not wired to workload {workload_name}")
            if sentinels[member].get("budget_classification") != workload.get("budget_classification"):
                raise RuntimeError(f"P-01 fixture {member} has a different workload budget")
    cases = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="elisa-p01-") as temp:
        tempdir = Path(temp)
        for name, fixture in FIXTURES:
            source = tempdir / f"{name}.elisa"
            source.write_bytes(fixture.read_bytes())
            scenarios: dict[str, list[dict]] = {}
            def record(label: str, input_path: Path, round_index: int) -> None:
                row = invoke(binary, input_path, args.timeout, args.rss_limit_kib)
                row["round"] = round_index
                try:
                    check_report(row, sentinels[name]["expected_outcome"],
                                 sentinels[name].get("semantic_expectations"))
                except RuntimeError as error:
                    row["validation_error"] = str(error)
                    failures.append(f"{name}/{label}/round-{round_index}: {error}")
                scenarios.setdefault(label, []).append(row)

            for warmup_index in range(warmup_runs):
                source.write_bytes(fixture.read_bytes())
                warmup = invoke(binary, source, args.timeout, args.rss_limit_kib)
                try:
                    check_report(warmup, sentinels[name]["expected_outcome"],
                                 sentinels[name].get("semantic_expectations"))
                except RuntimeError as error:
                    failures.append(f"{name}/warmup-{warmup_index + 1}: {error}")
            edit_source = None
            for round_index in range(1, rounds + 1):
                source.write_bytes(fixture.read_bytes())
                record("cold", source, round_index)
                record("warm", source, round_index)
                source.write_bytes(fixture.read_bytes() + b"\n# P-01 comment-only edit\n")
                record("no_op", source, round_index)
                if name == "real_small":
                    edit_source = tempdir / f"real_small_edit-{round_index}.elisa"
                    edit_source.write_bytes(
                        fixture.read_bytes().replace(b"value == value", b"value == value + 0", 1))
                    record("edit", edit_source, round_index)
            cases.append({"name": name, "source": identity(fixture),
                          "comment_edit_source": identity(source),
                          **({"edit_source": identity(edit_source)} if edit_source else {}),
                          "scenarios": {key: {"measurements": values, **summarize(values)}
                                        for key, values in scenarios.items()}})
    if fixture_ids != {name: identity(path) for name, path in FIXTURES}:
        raise RuntimeError("a fixed workload changed during measurement")
    if build_identity(binary) != build:
        raise RuntimeError("P-01 proof build identity changed during measurement")
    if build_identity(replay_binary) != replay_build:
        raise RuntimeError("P-01 standalone replay build identity changed during measurement")
    fixture_rows = []
    for name, path in FIXTURES:
        sentinel = sentinels[name]
        fixture_row = {"name": name, "path": str(path), "sha256": fixture_ids[name]["sha256"],
                       "size_bytes": fixture_ids[name]["size_bytes"],
                       "expected_outcome": sentinel["expected_outcome"]}
        if "semantic_expectations" in sentinel:
            fixture_row["semantic_expectations"] = sentinel["semantic_expectations"]
        for optional_key in ("workload", "budget_classification"):
            if optional_key in sentinel:
                fixture_row[optional_key] = sentinel[optional_key]
        fixture_rows.append(fixture_row)
    return {"schema": SCHEMA, "complete": not failures, "failures": failures,
            "machine": {"platform": platform.platform(),
            "python": platform.python_version(), "target": platform.machine(),
            "concurrency": 1}, "rounds": rounds, "warmup_runs_per_fixture": warmup_runs,
            "limits": {"timeout_seconds": args.timeout,
            "rss_kib": args.rss_limit_kib, "output_bytes": MAX_OUTPUT_BYTES},
            "binary": {"path": str(binary), **identity(binary)},
            "build": build,
            # These identities come from the manifest bound to the selected binary. Looking at
            # the caller's checkout here can silently describe a different build's frontend or
            # runtime when --binary points at an isolated build directory.
            "frontend": build["frontend"],
            "runtime": build["runtime"],
            "counter_availability": {"goal_cache_hits": "serialized-per-proof-report", "goal_cache_misses": "serialized-per-proof-report",
                "control_flow_steps": "serialized-per-proof-report", "live_facts_peak": "serialized-per-proof-report",
                **{name: ("unavailable-not-emitted-by-proof-cli" if source is None else source)
                   for name, source in SHAPE_METRICS.items()},
                "goal_attempt_and_cache_counts": "serialized-per-proof-report",
                "kernel_node_child_and_replay_counts": "serialized-per-proof-report"},
            "phase_timing_availability": PHASE_TIMING_AVAILABILITY,
            "fixtures": fixture_rows,
            "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/elisa-proof")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--rss-limit-kib", type=int, default=1_500_000)
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--warmup-runs", type=int, default=1)
    args = parser.parse_args()
    if args.timeout <= 0 or args.rss_limit_kib <= 0 or args.rounds <= 0 or args.warmup_runs < 0:
        parser.error("timeout, RSS limit and rounds must be positive; warm-up runs cannot be negative")
    try:
        report = run(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, RuntimeError) as error:
        print(f"P-01 baseline failed: {error}", file=sys.stderr)
        return 2
    print(f"P-01 baseline written: {args.output}")
    if not report["complete"]:
        print(f"P-01 baseline incomplete: {len(report['failures'])} bounded/report validation failure(s)", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
