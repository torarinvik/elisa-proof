"""Semantic report validation and measurement summaries for the Luna benchmark."""

from __future__ import annotations

import json
import math
import statistics


def check_exit(result: dict, expected: int, label: str) -> None:
    if result["returncode"] != expected:
        stderr = result["stderr"].decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"{label}: expected exit {expected}, got {result['returncode']}; {stderr}")


def proof_report(result: dict, expected_status: str, label: str,
                 must_unproven: tuple[str, ...] = (),
                 must_prove: tuple[str, ...] = (),
                 must_find: tuple[str, ...] = ()) -> dict:
    try:
        report = json.loads(result["stdout"])
    except (ValueError, KeyError) as error:
        raise RuntimeError(f"{label}: unexpected proof report or replay state") from error
    if not isinstance(report, dict) or not isinstance(report.get("replay"), dict):
        raise RuntimeError(f"{label}: proof report has an invalid top-level schema")
    if (not isinstance(report.get("goals"), list)
            or not isinstance(report.get("findings"), list)
            or not isinstance(report.get("functions"), list)):
        raise RuntimeError(f"{label}: proof report is missing goal, finding, or function arrays")
    if report.get("status") != expected_status:
        raise RuntimeError(f"{label}: expected status {expected_status}, got {report.get('status')}")
    replay = report.get("replay", {})
    if replay.get("gaps") != 0 or replay.get("certificates") != replay.get("replayed"):
        raise RuntimeError(f"{label}: proof report contains replay gaps or mismatched counts")
    if any(not isinstance(goal, dict) for goal in report["goals"]):
        raise RuntimeError(f"{label}: proof report contains an invalid goal record")
    if any(goal.get("proven") and goal.get("replay_status") != "replayed"
           for goal in report["goals"]):
        raise RuntimeError(f"{label}: a claimed proof lacks replay status")
    functions = report["functions"]
    if any(not isinstance(function, dict) for function in functions):
        raise RuntimeError(f"{label}: proof report contains an invalid function record")
    for name in must_unproven:
        matches = [function for function in functions if function.get("name") == name]
        if not matches or not any(function.get("open_goals", 0) > 0 for function in matches):
            raise RuntimeError(f"{label}: adversarial function {name!r} has no open goals")
    for name in must_prove:
        if not any(function.get("name") == name and function.get("proved") is True
                   for function in functions):
            raise RuntimeError(f"{label}: positive control function {name!r} was not proven")
    findings = {finding.get("name") for finding in report.get("findings", [])}
    if not set(must_find) <= findings:
        missing = sorted(set(must_find) - findings)
        raise RuntimeError(f"{label}: expected refusal findings are missing: {missing}")
    if must_find:
        claimed_functions = {function.get("name") for function in functions
                             if function.get("proved") is True}
        if set(must_find) & claimed_functions:
            raise RuntimeError(f"{label}: adversarial functions were claimed proven: {sorted(set(must_find) & claimed_functions)}")
    return report


def semantic_workload_metrics(result: dict, report: dict, label: str) -> dict:
    """Return semantic workload size only for a complete, replay-closed proof report."""
    try:
        summary = report["summary"]
        replay = report["replay"]
        declarations = report["declaration_details"]
        goals = report["goals"]
        certificates = report["certificates"]
        if not all(isinstance(value, dict) for value in (summary, replay)):
            raise ValueError("summary/replay is not an object")
        if not all(isinstance(value, list) for value in (declarations, goals, certificates)):
            raise ValueError("declarations/goals/certificates is not an array")
        declaration_count = summary["declarations"]
        obligation_count = summary["obligations"]
        certificate_count = replay["certificates"]
        replayed_count = replay["replayed"]
        replay_gaps = replay["gaps"]
        proven_count = summary["proven"]
        unproven_count = summary["unproven"]
        if any(type(value) is not int or value < 0 for value in (
                declaration_count, obligation_count, certificate_count,
                replayed_count, replay_gaps, proven_count, unproven_count)):
            raise ValueError("count field is missing or invalid")
        if declaration_count != len(declarations) or obligation_count != len(goals):
            raise ValueError("declaration/obligation arrays are incomplete")
        if certificate_count != len(certificates) or replayed_count != certificate_count or replay_gaps != 0:
            raise ValueError("certificate replay is incomplete")
        if proven_count + unproven_count != obligation_count:
            raise ValueError("obligation totals are incomplete")
        status = report.get("status")
        if status == "proved" and unproven_count == 0 and proven_count == obligation_count:
            classification = "proved"
        elif status == "failed" and unproven_count > 0:
            classification = "refusal"
        else:
            raise ValueError("report outcome is neither a complete proof nor a refusal")
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"{label}: incomplete semantic workload report: {error}") from error

    certificate_bytes = len(json.dumps(
        certificates, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8"))
    return {
        "classification": classification,
        "declarations": declaration_count,
        "verified_declarations": sum(1 for item in declarations
                                      if isinstance(item, dict) and item.get("verified") is True),
        "obligations": obligation_count,
        "proof_bytes": len(result["stdout"]),
        "certificate_count": certificate_count,
        "certificate_bytes_compact_json": certificate_bytes,
        "replayed_count": replayed_count,
        "replay_gaps": replay_gaps,
        "complete": True,
    }


def replay_result(result: dict, expected_status: str, expected_reason: str | None,
                  label: str) -> dict:
    try:
        replay = json.loads(result["stdout"])
    except (ValueError, KeyError) as error:
        raise RuntimeError(f"{label}: unexpected portable replay output") from error
    if not isinstance(replay, dict):
        raise RuntimeError(f"{label}: replay result has an invalid top-level schema")
    if replay.get("format") != "elisa-proof-replay-result-v1" or replay.get("status") != expected_status:
        raise RuntimeError(f"{label}: unexpected replay result format or status")
    if expected_status == "replayed":
        summary = replay.get("summary", {})
        if not isinstance(summary, dict):
            raise RuntimeError(f"{label}: replay result is missing its summary")
        if summary.get("theorems", 0) <= 0 or summary.get("not_replayed") != 0:
            raise RuntimeError(f"{label}: replay result does not cover every exported theorem")
    elif replay.get("reason") != expected_reason:
        raise RuntimeError(f"{label}: expected refusal reason {expected_reason!r}, got {replay.get('reason')!r}")
    trust = replay.get("trust", {})
    if not isinstance(trust, dict):
        raise RuntimeError(f"{label}: replay result has an invalid trust record")
    if trust.get("kernel") != "checked" or trust.get("source_authenticated") is not False:
        raise RuntimeError(f"{label}: replay trust record does not preserve the kernel boundary")
    return replay


def record_measurements(samples: list[dict]) -> dict:
    if not samples:
        raise RuntimeError("cannot summarize an empty or fully censored sample set")
    times = [sample["wall_seconds"] for sample in samples]
    user_cpu = [sample["user_cpu_seconds"] for sample in samples
                if sample.get("user_cpu_seconds") is not None]
    system_cpu = [sample["system_cpu_seconds"] for sample in samples
                  if sample.get("system_cpu_seconds") is not None]
    rss = [sample["peak_rss_kib"] for sample in samples]
    ordered_times = sorted(times)
    ordered_user_cpu = sorted(user_cpu)
    ordered_system_cpu = sorted(system_cpu)
    p95_index = max(0, math.ceil(0.95 * len(ordered_times)) - 1)
    user_cpu_p95_index = max(0, math.ceil(0.95 * len(ordered_user_cpu)) - 1) if user_cpu else None
    system_cpu_p95_index = max(0, math.ceil(0.95 * len(ordered_system_cpu)) - 1) if system_cpu else None
    return {
        "rounds": len(samples),
        "user_cpu_samples": len(user_cpu),
        "system_cpu_samples": len(system_cpu),
        "rss_samples": sum(value is not None for value in rss),
        "p50_wall_seconds": round(statistics.median(times), 6),
        "median_wall_seconds": round(statistics.median(times), 6),
        "p95_wall_seconds": round(ordered_times[p95_index], 6),
        "wall_spread_seconds": round(max(times) - min(times), 6),
        "minimum_wall_seconds": round(min(times), 6),
        "maximum_wall_seconds": round(max(times), 6),
        "p50_user_cpu_seconds": round(statistics.median(user_cpu), 6) if user_cpu else None,
        "p95_user_cpu_seconds": round(ordered_user_cpu[user_cpu_p95_index], 6)
            if user_cpu_p95_index is not None else None,
        "median_user_cpu_seconds": round(statistics.median(user_cpu), 6) if user_cpu else None,
        "p50_system_cpu_seconds": round(statistics.median(system_cpu), 6) if system_cpu else None,
        "p95_system_cpu_seconds": round(ordered_system_cpu[system_cpu_p95_index], 6)
            if system_cpu_p95_index is not None else None,
        "median_system_cpu_seconds": round(statistics.median(system_cpu), 6) if system_cpu else None,
        "peak_rss_kib": int(max(rss)) if all(value is not None for value in rss) else None,
    }


def measurement_self_test() -> None:
    samples = [
        {"wall_seconds": float(value), "user_cpu_seconds": float(value) / 2,
         "system_cpu_seconds": float(value) / 4, "peak_rss_kib": value * 10}
        for value in range(1, 8)
    ]
    measured = record_measurements(samples)
    if (measured["rounds"] != 7 or measured["median_wall_seconds"] != 4.0
            or measured["p95_wall_seconds"] != 7.0
            or measured["p50_wall_seconds"] != 4.0
            or measured["wall_spread_seconds"] != 6.0
            or measured["median_user_cpu_seconds"] != 2.0
            or measured["median_system_cpu_seconds"] != 1.0):
        raise RuntimeError(f"measurement summary statistics are incorrect: {measured}")
