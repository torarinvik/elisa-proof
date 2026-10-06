#!/usr/bin/env python3
"""P-01 proof CLI invocation, semantic-shape extraction, and admission checks."""

from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from p01_manifest import MAX_OUTPUT_BYTES, ROOT, SHAPE_METRICS

MEASURED_PHASE_TIMINGS = (
    "proof_cli_invocation_wall",
    "proof_cli_child_cpu",
    "baseline_harness_json_decode",
)


def shape_metrics(report: dict) -> dict:
    """Extract only counters explicitly emitted by the proof CLI; never infer AST shape."""
    source = report.get("source")
    files = report.get("files")
    measurements = report.get("measurements")
    replay = report.get("replay")
    summary = report.get("summary")
    declarations = report.get("declaration_details")
    if not isinstance(source, dict) or not isinstance(files, list) \
            or not isinstance(measurements, dict) or not isinstance(replay, dict) \
            or not isinstance(summary, dict) or not isinstance(declarations, list):
        raise RuntimeError("P-01 report lacks source, file-map, measurement, or replay data")
    declaration_count = measurements.get("declarations")
    if (declaration_count != summary.get("declarations")
            or declaration_count != len(declarations)
            or measurements.get("certificates") != replay.get("certificates")):
        raise RuntimeError("P-01 report shape counters disagree across serialized sections")
    values = {
        "source_imported_bytes": source.get("bytes"),
        "source_file_count": len(files),
        "token_count": None,
        "ast_node_count": None,
        "declaration_count": measurements.get("declarations"),
        "fact_trace_count": measurements.get("fact_traces"),
        "certificate_fact_count": measurements.get("certificate_facts"),
        "branch_count": None,
        "call_count": None,
        "loop_count": None,
        "certificate_count": replay.get("certificates"),
        "kernel_node_count": measurements.get("kernel_nodes"),
        "kernel_child_count": measurements.get("kernel_children"),
        "package_node_count": None,
    }
    for name, value in values.items():
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise RuntimeError(f"P-01 semantic-shape counter {name} is malformed")
        if (SHAPE_METRICS[name] is not None) != (value is not None):
            raise RuntimeError(f"P-01 semantic-shape counter {name} availability disagrees with its schema")
    return values

def process_rss_kib(pid: int) -> int | None:
    try:
        output = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True,
                                text=True, check=False, timeout=1).stdout.strip()
        return int(output) if output else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def wait4_peak_rss_kib(usage) -> int:
    """Normalize wait4's ru_maxrss, which is bytes on macOS and KiB on Linux."""
    value = max(0, int(getattr(usage, "ru_maxrss", 0)))
    if sys.platform == "darwin":
        return (value + 1023) // 1024
    return value


def invoke(binary: Path, source: Path, timeout: float, rss_limit_kib: int) -> dict:
    started = time.monotonic()
    # Spool directly to temporary files while the verifier runs. Deferring reads
    # from stdout/stderr PIPEs until exit deadlocks as soon as a legitimate large
    # JSON report fills the OS pipe buffer (observed at exactly 64 KiB).
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        proc = subprocess.Popen([str(binary), "--json", str(source)], cwd=ROOT,
                                stdout=stdout_file, stderr=stderr_file,
                                start_new_session=True)
        peak = 0
        stop = None
        cpu_seconds = None
        wait4_supported = hasattr(os, "wait4")
        while True:
            if wait4_supported:
                ended_pid, wait_status, usage = os.wait4(proc.pid, os.WNOHANG)
                if ended_pid:
                    proc.returncode = os.waitstatus_to_exitcode(wait_status)
                    cpu_seconds = usage.ru_utime + usage.ru_stime
                    peak = max(peak, wait4_peak_rss_kib(usage))
                    break
            elif proc.poll() is not None:
                break
            rss = process_rss_kib(proc.pid)
            if rss is not None:
                peak = max(peak, rss)
            output_bytes = (os.fstat(stdout_file.fileno()).st_size
                            + os.fstat(stderr_file.fileno()).st_size)
            if time.monotonic() - started >= timeout:
                stop = "timeout"
            elif peak >= rss_limit_kib:
                stop = "rss_limit"
            elif output_bytes > MAX_OUTPUT_BYTES:
                stop = "output_limit"
            if stop:
                proc_kill_fallback = False
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    # Some hosts deny signaling a process group even though the
                    # caller owns the child. Prefer os.kill here: Popen.kill()
                    # polls (and may reap) the child with waitpid, racing the
                    # wait4 below and losing child resource usage.
                    try:
                        os.kill(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        # Only use Popen's fallback if direct signaling is denied.
                        # In that rare path, Popen may reap the child internally,
                        # so do not call wait4 afterward.
                        try:
                            proc.kill()
                        except ProcessLookupError:
                            pass
                        proc_kill_fallback = True
                if wait4_supported and not proc_kill_fallback:
                    _, wait_status, usage = os.wait4(proc.pid, 0)
                    proc.returncode = os.waitstatus_to_exitcode(wait_status)
                    cpu_seconds = usage.ru_utime + usage.ru_stime
                    peak = max(peak, wait4_peak_rss_kib(usage))
                else:
                    proc.wait()
                break
            time.sleep(0.025)
        if proc.returncode is None:
            proc.wait()
        stdout_bytes = os.fstat(stdout_file.fileno()).st_size
        stderr_bytes = os.fstat(stderr_file.fileno()).st_size
        if stop is None and stdout_bytes + stderr_bytes > MAX_OUTPUT_BYTES:
            stop = "output_limit"
        stdout_file.seek(0)
        stdout = stdout_file.read(MAX_OUTPUT_BYTES + 1)
        stderr_file.seek(max(0, stderr_bytes - 2000))
        stderr = stderr_file.read()
    elapsed = time.monotonic() - started
    result = {"wall_seconds": elapsed, "cpu_seconds": cpu_seconds, "peak_rss_kib": peak,
              "returncode": proc.returncode, "stop_reason": stop,
              "report_complete": False, "stdout_bytes": stdout_bytes,
              "stderr_bytes": stderr_bytes, "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
              "stdout_sha256_bytes": len(stdout), "stdout_sha256_complete": len(stdout) == stdout_bytes,
              "stderr_tail_bytes": len(stderr), "stderr_tail_sha256": hashlib.sha256(stderr).hexdigest()}
    # These durations are observed by the harness; they are not internal proof-stage times.
    # Invocation wall includes process launch, waiting, and captured-output handling.
    result["phase_timings_seconds"] = {
        "proof_cli_invocation_wall": elapsed,
        "proof_cli_child_cpu": cpu_seconds,
        "baseline_harness_json_decode": None,
    }
    if stop:
        return result
    decode_started = time.monotonic()
    try:
        report = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        result["phase_timings_seconds"]["baseline_harness_json_decode"] = time.monotonic() - decode_started
        result["stdout_sha256"] = hashlib.sha256(stdout).hexdigest()
        return result
    result["phase_timings_seconds"]["baseline_harness_json_decode"] = time.monotonic() - decode_started
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
        "source_obligation_inventory": report.get("source_obligation_inventory"),
        "semantic_shape": shape_metrics(report),
        "obligation_ids": [goal.get("goal_id") for goal in goals],
        "obligation_details": [{"id": goal.get("goal_id"), "function": goal.get("name"),
                                "line": goal.get("line"), "rule": goal.get("rule"),
                                "result": "proved" if goal.get("proven") is True else "unproven"}
                               for goal in goals],
        "failed": summary.get("failed"),
        "proof_certificates": measurements.get("certificates"),
        "trusted_assumptions": len(report.get("trust", {}).get("trusted_assumptions", [])),
        "trusted_assumption_details": report.get("trust", {}).get("trusted_assumptions", []),
        "trusted_boundary_facts": report.get("trust", {}).get("trusted_boundary_facts"),
        # Preserve the complete CLI measurement object. This keeps newly emitted serialized
        # counters available to baseline consumers without implying internal timing coverage.
        "proof_report_measurements": measurements,
        "goal_cache_hits": measurements.get("goal_cache_hits"),
        "goal_cache_misses": measurements.get("goal_cache_misses"),
        "control_flow_steps": measurements.get("control_flow_steps"),
        "live_facts_peak": measurements.get("live_facts_peak"),
    })
    return result


def check_report(measurement: dict, expected: dict | None = None,
                 semantic_expectations: dict | None = None) -> None:
    if measurement["stop_reason"]:
        raise RuntimeError(f"bounded failure: {measurement['stop_reason']}")
    if not measurement["report_complete"]:
        raise RuntimeError("proof process did not emit a complete JSON report")
    inventory = measurement.get("source_obligation_inventory")
    if (not isinstance(inventory, dict) or inventory.get("whole_program") is not True
            or inventory.get("coverage") != "complete"):
        raise RuntimeError("source obligation inventory is incomplete or not whole-program")
    observed_shape = measurement.get("semantic_shape")
    if not isinstance(observed_shape, dict) or set(observed_shape) != set(SHAPE_METRICS):
        raise RuntimeError("semantic-shape measurements are incomplete")
    for name, value in observed_shape.items():
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise RuntimeError(f"semantic-shape measurement {name} is malformed")
        if (SHAPE_METRICS[name] is not None) != (value is not None):
            raise RuntimeError(f"semantic-shape measurement {name} availability is inconsistent")
    if not isinstance(measurement.get("cpu_seconds"), (int, float)):
        raise RuntimeError("proof process CPU time is unavailable on this host")
    phase_timings = measurement.get("phase_timings_seconds")
    if not isinstance(phase_timings, dict) or set(phase_timings) != set(MEASURED_PHASE_TIMINGS):
        raise RuntimeError("report has a missing or unexpected phase-timing schema")
    for phase in MEASURED_PHASE_TIMINGS:
        value = phase_timings[phase]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise RuntimeError(f"report has an invalid {phase} duration")
    if phase_timings["proof_cli_invocation_wall"] != measurement.get("wall_seconds"):
        raise RuntimeError("phase timing disagrees with proof CLI invocation wall time")
    if phase_timings["proof_cli_child_cpu"] != measurement.get("cpu_seconds"):
        raise RuntimeError("phase timing disagrees with proof CLI child CPU time")
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
    if semantic_expectations:
        if semantic_expectations.get("obligation_inventory_complete") is not True:
            raise RuntimeError("source obligation inventory is incomplete")
        if (measurement.get("obligations") != len(measurement.get("obligation_ids", []))
                or measurement.get("obligations") != len(measurement.get("obligation_details", []))):
            raise RuntimeError("reported obligation count differs from emitted obligation inventory")
        for key in ("obligation_count", "proven", "unproven", "failed", "trusted_assumptions",
                    "trusted_boundary_facts", "proof_certificates", "replay_certificates",
                    "replayed", "replay_gaps"):
            observed_key = "obligations" if key == "obligation_count" else key
            if measurement.get(observed_key) != semantic_expectations[key]:
                raise RuntimeError(f"unexpected {observed_key}: {measurement.get(observed_key)}")
        if measurement.get("obligation_ids") != semantic_expectations["obligation_ids"]:
            raise RuntimeError("obligation IDs differ from the pinned semantic workload")
        if measurement.get("obligation_details") != semantic_expectations["obligation_details"]:
            raise RuntimeError("obligation details differ from the pinned semantic workload")
        if measurement.get("trusted_assumption_details") != semantic_expectations["trusted_assumption_details"]:
            raise RuntimeError("trusted assumptions differ from the pinned semantic workload")
