#!/usr/bin/env python3
"""Bounded P-01 proof CLI baseline. Does not build, install, or alter repository files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "elisa-proof-p01-baseline-v1"
FIXTURES = (
    ("real_small", ROOT / "examples/perf_luna_accept.elisa"),
    ("real_refusal", ROOT / "examples/perf_luna_refusal.elisa"),
    ("adversarial", ROOT / "examples/rejected_symbolic_quantifier.elisa"),
)
EXPECTED_OUTCOMES = {
    "real_small": {"status": "proved", "returncode": 0},
    "real_refusal": {"status": "failed", "returncode": 1},
    # The bounded symbolic-quantifier case may time out; if it emits a complete report,
    # it must remain a non-proof with the CLI's ordinary refusal exit code.
    "adversarial": {"not_proved": True, "returncode": 1},
}


def identity(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def process_rss_kib(pid: int) -> int | None:
    try:
        output = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True,
                                text=True, check=False, timeout=1).stdout.strip()
        return int(output) if output else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def invoke(binary: Path, source: Path, timeout: float, rss_limit_kib: int) -> dict:
    started = time.monotonic()
    proc = subprocess.Popen([str(binary), "--json", str(source)], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    peak = 0
    stop = None
    while proc.poll() is None:
        rss = process_rss_kib(proc.pid)
        if rss is not None:
            peak = max(peak, rss)
        if time.monotonic() - started >= timeout:
            stop = "timeout"
        elif peak >= rss_limit_kib:
            stop = "rss_limit"
        if stop:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            break
        time.sleep(0.025)
    stdout, stderr = proc.communicate()
    elapsed = time.monotonic() - started
    result = {"wall_seconds": elapsed, "peak_rss_kib": peak,
              "returncode": proc.returncode, "stop_reason": stop,
              "report_complete": False, "stderr_sha256": hashlib.sha256(stderr).hexdigest()}
    if stop:
        return result
    try:
        report = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        result["stdout_sha256"] = hashlib.sha256(stdout).hexdigest()
        return result
    summary = report.get("summary", {})
    replay = report.get("replay", {})
    measurements = report.get("measurements", {})
    declarations = report.get("declaration_details", [])
    goals = report.get("goals", [])
    result.update({
        "report_complete": isinstance(summary, dict) and isinstance(replay, dict)
            and isinstance(measurements, dict),
        "status": report.get("status"),
        "verification_state": report.get("verification_state"),
        "obligations": summary.get("obligations"), "proven": summary.get("proven"),
        "unproven": summary.get("unproven"), "semantic_errors": summary.get("semantic_errors"),
        "declarations": len(declarations), "verified_declarations": sum(
            1 for item in declarations if item.get("verified") is True),
        "goals": len(goals), "replay_certificates": replay.get("certificates"),
        "replayed": replay.get("replayed"), "replay_gaps": replay.get("gaps"),
        "goal_cache_hits": measurements.get("goal_cache_hits"),
        "goal_cache_misses": measurements.get("goal_cache_misses"),
        "control_flow_steps": measurements.get("control_flow_steps"),
        "live_facts_peak": measurements.get("live_facts_peak"),
    })
    return result


def check_report(measurement: dict, expected: dict | None = None) -> None:
    if measurement["stop_reason"]:
        raise RuntimeError(f"bounded failure: {measurement['stop_reason']}")
    if not measurement["report_complete"]:
        raise RuntimeError("proof process did not emit a complete JSON report")
    if measurement["replay_gaps"] != 0:
        raise RuntimeError(f"report contains replay gaps: {measurement['replay_gaps']}")
    if measurement["replay_certificates"] != measurement["replayed"]:
        raise RuntimeError("report contains certificates without corresponding replay")
    for counter in ("goal_cache_hits", "goal_cache_misses", "control_flow_steps", "live_facts_peak"):
        value = measurement.get(counter)
        if not isinstance(value, int) or value < 0:
            raise RuntimeError(f"report is missing a valid {counter} measurement")
    if expected:
        if expected.get("not_proved") and measurement["status"] == "proved":
            raise RuntimeError("negative fixture was accepted as proved")
        if "status" in expected and measurement["status"] != expected["status"]:
            raise RuntimeError(f"unexpected proof status: {measurement['status']}")
        if measurement["returncode"] != expected["returncode"]:
            raise RuntimeError(f"unexpected CLI exit code: {measurement['returncode']}")


def summarize(rows: list[dict]) -> dict:
    times = [row["wall_seconds"] for row in rows]
    return {"runs": len(rows), "median_wall_seconds": statistics.median(times),
            "p95_wall_seconds": sorted(times)[max(0, (95 * len(times) + 99) // 100 - 1)],
            "max_peak_rss_kib": max(row["peak_rss_kib"] for row in rows)}


def run(args: argparse.Namespace) -> dict:
    binary = args.binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(f"proof binary is not executable: {binary}")
    fixture_ids = {name: identity(path) for name, path in FIXTURES}
    cases = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="elisa-p01-") as temp:
        tempdir = Path(temp)
        for name, fixture in FIXTURES:
            source = tempdir / f"{name}.elisa"
            source.write_bytes(fixture.read_bytes())
            scenarios: dict[str, list[dict]] = {}
            for label in ("cold", "warm", "no_op"):
                if label == "no_op":
                    source.write_bytes(fixture.read_bytes() + b"\n# P-01 comment-only edit\n")
                row = invoke(binary, source, args.timeout, args.rss_limit_kib)
                try:
                    check_report(row, EXPECTED_OUTCOMES.get(name))
                except RuntimeError as error:
                    row["validation_error"] = str(error)
                    failures.append(f"{name}/{label}: {error}")
                scenarios.setdefault(label, []).append(row)
            if name == "real_small":
                edited = tempdir / "real_small_edit.elisa"
                edited.write_bytes(fixture.read_bytes().replace(b"value == value", b"value == value + 0", 1))
                row = invoke(binary, edited, args.timeout, args.rss_limit_kib)
                try:
                    check_report(row, EXPECTED_OUTCOMES.get(name))
                except RuntimeError as error:
                    row["validation_error"] = str(error)
                    failures.append(f"{name}/edit: {error}")
                scenarios["edit"] = [row]
                cases.append({"name": name, "source": identity(fixture),
                              "comment_edit_source": identity(source), "edit_source": identity(edited),
                              "scenarios": {key: {"measurements": values, **summarize(values)}
                                            for key, values in scenarios.items()}})
            else:
                cases.append({"name": name, "source": identity(fixture),
                              "comment_edit_source": identity(source),
                              "scenarios": {key: {"measurements": values, **summarize(values)}
                                            for key, values in scenarios.items()}})
    if fixture_ids != {name: identity(path) for name, path in FIXTURES}:
        raise RuntimeError("a fixed workload changed during measurement")
    frontend_pin = ROOT / "build/frontend.pin"
    runtime_obj = ROOT / "build/runtime/elisacore_runtime.o"
    return {"schema": SCHEMA, "complete": not failures, "failures": failures,
            "machine": {"platform": platform.platform(),
            "python": platform.python_version(), "target": platform.machine(),
            "concurrency": 1}, "limits": {"timeout_seconds": args.timeout,
            "rss_kib": args.rss_limit_kib}, "binary": {"path": str(binary), **identity(binary)},
            "frontend": ({"path": str(frontend_pin), **identity(frontend_pin)}
                         if frontend_pin.is_file() else {"identity": "unavailable"}),
            "runtime": ({"path": str(runtime_obj), **identity(runtime_obj)}
                        if runtime_obj.is_file() else {"identity": "unavailable"}),
            "counter_availability": {"goal_cache_hits": "serialized-per-proof-report", "goal_cache_misses": "serialized-per-proof-report",
                "control_flow_steps": "serialized-per-proof-report", "live_facts_peak": "serialized-per-proof-report",
                "source_import_parse_semantics_search_replay_reporting_stage_times": "not instrumented"},
            "fixtures": [{"name": name, "path": str(path), "sha256": fixture_ids[name]["sha256"],
                          "size_bytes": fixture_ids[name]["size_bytes"],
                          "expected_outcome": EXPECTED_OUTCOMES.get(name)} for name, path in FIXTURES],
            "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/elisa-proof")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--rss-limit-kib", type=int, default=1_500_000)
    args = parser.parse_args()
    if args.timeout <= 0 or args.rss_limit_kib <= 0:
        parser.error("timeout and RSS limit must be positive")
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
