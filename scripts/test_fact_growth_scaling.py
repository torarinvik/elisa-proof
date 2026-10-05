#!/usr/bin/env python3
"""Bounded, one-axis-at-a-time fact/branch growth probes (R-013).

This is a measurement harness, not a performance benchmark: it records semantic and
replay outcomes plus counters already exposed by the proof report. Wall time is not
used to infer asymptotic work.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RSS_KIB = 2 * 1024 * 1024
SIZES = (1, 2, 4, 8, 12, 16)
DUPLICATE_SIZES = (0, 1, 2, 4, 8, 12, 13)
MEASUREMENT_KEYS = (
    "declarations", "obligations", "goal_attempts", "certificates",
    "certificate_facts", "largest_certificate_facts", "repeated_certificate_fact_roots",
    "fact_traces", "control_flow_steps", "live_facts_peak", "goal_cache_hits",
    "goal_cache_misses", "kernel_nodes", "kernel_nodes_shared", "kernel_children",
    "report_bytes",
)


def relevant_source(size):
    names = [f"x{index}" for index in range(size + 1)]
    params = ", ".join(f"{name}: i64" for name in names)
    requires = [f"    requires {names[0]} >= 0"]
    requires.extend(f"    requires {names[index]} >= {names[index - 1]}"
                    for index in range(1, len(names)))
    return "\n".join([
        f"def relevant_growth_{size}({params}) -> i64:", *requires,
        "    ensure result >= 0", f"    return {names[-1]}", "",
    ])


def irrelevant_source(size):
    requires = ["    requires x >= 0"]
    # Distinct, mutually consistent upper bounds that do not help prove 0 >= 0.
    requires.extend(f"    requires x <= {index}" for index in range(size))
    return "\n".join([
        f"def irrelevant_growth_{size}(x: i64) -> i64:", *requires,
        "    ensure result >= 0", "    return 0", "",
    ])


def duplicate_source(size):
    requires = ["    requires x >= -2", "    requires x <= 2"]
    requires.extend("    requires FactGrowthConstants::C == FactGrowthConstants::C"
                    for _ in range(size))
    return "\n".join([
        "module FactGrowthConstants:", "    const C: i64 = 1", "",
        f"def duplicate_growth_{size}(x: i64) -> i64:", *requires,
        "    ensure result >= 0", "    return x * x", "",
    ])


def branch_source(width):
    arms = [f"        {index}:\n            0" for index in range(width)]
    arms.append("        _:\n            0")
    return "\n".join([
        f"def branch_width_{width}(x: i64) -> i64:",
        "    ensure result >= 0", "    return match x:", *arms, "",
    ])


def sample_sources():
    for size in SIZES:
        yield "relevant-facts", size, relevant_source(size)
        yield "irrelevant-facts", size, irrelevant_source(size)
        yield "branch-width", size, branch_source(size)
    for size in DUPLICATE_SIZES:
        yield "duplicate-facts", size, duplicate_source(size)


def sampled_group_rss_kib(process_group):
    try:
        result = subprocess.run(["ps", "-axo", "pgid=,rss="],
                                capture_output=True, text=True, timeout=1, check=False)
        if result.returncode != 0:
            return None
        rss_values = [int(fields[1]) for line in result.stdout.splitlines()
                      if len(fields := line.split()) == 2
                      and fields[0].isdigit() and int(fields[0]) == process_group
                      and fields[1].isdigit()]
        return sum(rss_values) if rss_values else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def time_command():
    if platform.system() == "Darwin":
        return ["/usr/bin/time", "-l"]
    return ["/usr/bin/time", "-f", "__MAX_RSS_KIB__=%M"]


def exact_peak_rss_kib(stderr):
    if platform.system() == "Darwin":
        match = re.search(r"([0-9]+)\s+maximum resident set size", stderr)
        return (int(match.group(1)) + 1023) // 1024 if match else None
    match = re.search(r"__MAX_RSS_KIB__=([0-9]+)", stderr)
    return int(match.group(1)) if match else None


def run_case(path, timeout_seconds, max_rss_kib):
    with tempfile.TemporaryDirectory(prefix="elisa-r013-case-") as temp:
        stdout_path = Path(temp) / "stdout.json"
        stderr_path = Path(temp) / "stderr.txt"
        started = time.monotonic()
        peak_rss = 0
        rss_samples = 0
        reason = None
        with stdout_path.open("w+") as stdout, stderr_path.open("w+") as stderr:
            process = subprocess.Popen(
                [*time_command(), str(BINARY), "--json", str(path)],
                stdout=stdout, stderr=stderr,
                start_new_session=True,
            )
            while process.poll() is None:
                rss = sampled_group_rss_kib(process.pid)
                if rss is not None:
                    rss_samples += 1
                    peak_rss = max(peak_rss, rss)
                    if rss > max_rss_kib:
                        reason = "rss-limit"
                if reason is None and time.monotonic() - started > timeout_seconds:
                    reason = "timeout"
                if reason is not None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.025)
            returncode = process.wait()
            elapsed = time.monotonic() - started
            stdout.flush()
            stderr.flush()
        output = stdout_path.read_text()
        error = stderr_path.read_text()
    exact_rss = exact_peak_rss_kib(error)
    if exact_rss is not None:
        peak_rss = max(peak_rss, exact_rss)
        rss_samples += 1
        if exact_rss > max_rss_kib:
            reason = "rss-limit"

    report = None
    parse_error = None
    try:
        report = json.loads(output)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)
    measurements = report.get("measurements", {}) if report else {}
    metrics = {key: measurements.get(key) for key in MEASUREMENT_KEYS}
    goals = report.get("goals", []) if report else []
    goal_outcomes = [{
        "name": goal.get("name"),
        "rule": goal.get("rule"),
        "proven": goal.get("proven"),
        "replay_status": goal.get("replay_status"),
        "refusal_gate": goal.get("refusal_gate"),
    } for goal in goals]
    replay = report.get("replay", {}) if report else {}
    replay_inconsistent = bool(report) and (
        replay.get("gaps") != 0
        or replay.get("certificates") != replay.get("replayed")
    )
    if reason:
        outcome = reason
    elif parse_error:
        outcome = "invalid-report"
    elif report.get("summary", {}).get("semantic_errors", 0):
        outcome = "semantic-error"
    elif replay_inconsistent:
        outcome = "replay-inconsistent"
    elif report.get("verification_state") == "proved":
        outcome = "proved" if report.get("replay", {}).get("gaps") == 0 else "proved-with-replay-gaps"
    elif report.get("verification_state") == "unknown":
        outcome = "unknown/refused"
    else:
        outcome = str(report.get("verification_state", "missing"))
    return {
        "outcome": outcome,
        "exit_code": returncode,
        "wall_seconds": round(elapsed, 6),
        "peak_rss_kib": peak_rss if rss_samples else None,
        "rss_samples": rss_samples,
        "semantic_errors": report.get("summary", {}).get("semantic_errors") if report else None,
        "status": report.get("status") if report else None,
        "verification_state": report.get("verification_state") if report else None,
        "proofs": sum(1 for goal in goals if goal.get("proven")),
        "obligations": len(goals) if report else None,
        "goal_outcomes": goal_outcomes,
        "replay_gaps": replay.get("gaps") if report else None,
        "replay_certificates": replay.get("certificates") if report else None,
        "replayed_certificates": replay.get("replayed") if report else None,
        "measurements": metrics,
        "stderr_tail": error[-1000:],
        "report_parse_error": parse_error,
    }


def verify_fixed_controls(binary):
    env = dict(os.environ, ELISA_PROOF_BIN=str(binary))
    controls = (
        ROOT / "scripts/test_fact_growth_work_budget.py",
        ROOT / "scripts/test_bounded_model_work_budget.py",
    )
    results = []
    for test in controls:
        result = subprocess.run(["python3", str(test)], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=120, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"control failed: {test.name}: {result.stdout}\n{result.stderr}")
        results.append({"test": test.name, "stdout": result.stdout.strip()})
    return results


def encode_evidence(payload):
    """Keep the JSON concise: one compact record per case, readable metadata lines."""
    entries = list(payload.items())
    lines = ["{"]
    for index, (key, value) in enumerate(entries):
        suffix = "," if index + 1 < len(entries) else ""
        encoded_key = json.dumps(key)
        if key == "results":
            lines.append(f"  {encoded_key}: [")
            for row_index, row in enumerate(value):
                row_suffix = "," if row_index + 1 < len(value) else ""
                compact_row = json.dumps(row, sort_keys=True, separators=(",", ":"))
                lines.append(f"    {compact_row}{row_suffix}")
            lines.append(f"  ]{suffix}")
        else:
            compact_value = json.dumps(value, sort_keys=True, separators=(",", ":"))
            lines.append(f"  {encoded_key}: {compact_value}{suffix}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="write the machine-readable evidence JSON here")
    parser.add_argument("--timeout-seconds", type=float,
                        default=float(os.environ.get("ELISA_FACT_GROWTH_TIMEOUT_SECONDS",
                                                     DEFAULT_TIMEOUT_SECONDS)))
    parser.add_argument("--max-rss-kib", type=int,
                        default=int(os.environ.get("ELISA_FACT_GROWTH_MAX_RSS_KIB",
                                                  DEFAULT_MAX_RSS_KIB)))
    args = parser.parse_args()
    if not BINARY.is_file() or not os.access(BINARY, os.X_OK):
        raise SystemExit(f"proof product is not executable: {BINARY}")
    if args.timeout_seconds <= 0 or args.max_rss_kib <= 0:
        raise SystemExit("timeout and RSS limit must be positive")

    controls = verify_fixed_controls(BINARY)
    results = []
    with tempfile.TemporaryDirectory(prefix="elisa-r013-scaling-") as temp:
        temp_root = Path(temp)
        for axis, size, source in sample_sources():
            source_path = temp_root / f"{axis}-{size}.elisa"
            source_path.write_text(source)
            row = run_case(source_path, args.timeout_seconds, args.max_rss_kib)
            results.append({
                "axis": axis,
                "size": size,
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                **row,
            })

    payload = {
        "schema": "elisa-fact-growth-scaling-v1",
        "product": str(BINARY.resolve()),
        "controls": controls,
        "limits": {
            "per_case_timeout_seconds": args.timeout_seconds,
            "per_case_sampled_rss_kib": args.max_rss_kib,
            "rss_sampling_interval_seconds": 0.025,
            "rss_sampling_method": "sampled process-group RSS plus /usr/bin/time exact command peak; kill process group above sampled cap",
            "wall_time_interpretation": "descriptive only; not an asymptotic work estimate",
        },
        "sizes": {"single_axis_fact_sweeps": list(SIZES),
                  "duplicate_fact_sweep": list(DUPLICATE_SIZES)},
        "available_counters": list(MEASUREMENT_KEYS),
        "results": results,
        "unavailable_counters": [
            "goal_cache_key_fact_candidates (field/counter absent from this source and report schema)",
            "per-goal fact visits outside goal-cache-key hashing",
            "predicate/term-comparison counts and total symbolic solver work",
            "branch/fork count and branch-join work",
            "allocation count/bytes and per-phase allocation peaks",
            "per-goal elapsed CPU time and exact per-goal peak memory",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_evidence(payload))
    invalid = [row for row in results if row["outcome"] not in ("proved", "unknown/refused")]
    if invalid:
        raise RuntimeError(f"invalid scaling result(s), evidence retained at {args.output}: {invalid}")
    duplicate_rows = {row["size"]: row for row in results if row["axis"] == "duplicate-facts"}
    if duplicate_rows[12]["outcome"] != "proved" or duplicate_rows[13]["outcome"] != "unknown/refused":
        raise RuntimeError(f"12/13 duplicate controls changed, evidence retained at {args.output}")
    print(f"fact-growth scaling: wrote {len(results)} bounded cases to {args.output}")


if __name__ == "__main__":
    main()
