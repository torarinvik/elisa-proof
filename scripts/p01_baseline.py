#!/usr/bin/env python3
"""Bounded P-01 proof CLI baseline. Does not build, install, or alter repository files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
SCHEMA = "elisa-proof-p01-baseline-v3"
SENTINEL_MANIFEST = ROOT / "scripts" / "p01_sentinels.json"
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
FIXTURES = (
    ("real_small", ROOT / "examples/perf_luna_accept.elisa"),
    ("real_refusal", ROOT / "examples/perf_luna_refusal.elisa"),
    # Dogfood the proof kernel itself as a pinned real-code baseline fixture.
    ("proof_kernel_core", ROOT / "src/proof/kernel_core.elisa"),
    ("adversarial", ROOT / "examples/rejected_symbolic_quantifier.elisa"),
    ("qualified_constants", ROOT / "examples/qualified_constants_statements.elisa"),
    ("qualified_constant_refusal", ROOT / "examples/rejected_qualified_constants_statements.elisa"),
    ("unsigned_boundary_refusal", ROOT / "examples/counterexample_unsigned_boundaries.elisa"),
    ("quantifier_success", ROOT / "examples/quantifier.elisa"),
    ("region_lending_success", ROOT / "examples/region_lend_calls.elisa"),
    ("branch_join", ROOT / "examples/branch_join.elisa"),
    ("rejected_branch_join", ROOT / "examples/rejected_branch_join.elisa"),
)
def load_sentinel_manifest() -> dict:
    try:
        payload = json.loads(SENTINEL_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read P-01 sentinel manifest: {error}") from error
    if payload.get("schema") != "elisa-proof-p01-sentinels-v3" or not isinstance(payload.get("fixtures"), dict):
        raise RuntimeError("P-01 sentinel manifest has an unsupported schema")
    fixtures = payload["fixtures"]
    probe = payload.get("semantic_probe")
    probe_keys = ("proof_head", "proof_source_tree_sha256", "compiler_source_revision",
                  "compiler_product_sha256", "frontend_tree", "runtime_sha256",
                  "proof_binary_sha256", "replay_binary_sha256", "target", "optimization",
                  "compile_mode", "generation")
    if not isinstance(probe, dict) or any(not isinstance(probe.get(key), str) or not probe[key]
                                          for key in probe_keys):
        raise RuntimeError("P-01 semantic probe provenance is missing or incomplete")
    probe_hashes = ("proof_source_tree_sha256", "compiler_product_sha256",
                    "runtime_sha256", "proof_binary_sha256", "replay_binary_sha256")
    if any(len(probe[key]) != 64 or any(char not in "0123456789abcdef" for char in probe[key])
           for key in probe_hashes):
        raise RuntimeError("P-01 semantic probe provenance contains a malformed digest")
    for key in ("proof_head", "compiler_source_revision", "frontend_tree"):
        if len(probe[key]) != 40 or any(char not in "0123456789abcdef" for char in probe[key]):
            raise RuntimeError("P-01 semantic probe provenance contains a malformed revision")
    expected_names = {name for name, _ in FIXTURES}
    if set(fixtures) != expected_names:
        raise RuntimeError("P-01 fixtures do not match the versioned sentinel manifest")
    semantic_counts = ("obligation_count", "proven", "unproven", "failed",
                       "obligation_detail_proven", "obligation_detail_unproven",
                       "trusted_assumptions", "trusted_boundary_facts", "proof_certificates",
                       "replay_certificates", "replayed", "replay_gaps")
    for name, row in fixtures.items():
        if not isinstance(row, dict):
            raise RuntimeError(f"P-01 workload identity is malformed for {name}")
        digest = row.get("sha256")
        size = row.get("size_bytes")
        line_count = row.get("source_lines")
        if (not isinstance(row.get("path"), str) or not row["path"]
                or not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
                or isinstance(size, bool) or not isinstance(size, int) or size < 0
                or isinstance(line_count, bool) or not isinstance(line_count, int) or line_count < 0):
            raise RuntimeError(f"P-01 workload identity is incomplete for {name}")
        outcome = row.get("expected_outcome")
        if (not isinstance(outcome, dict)
                or outcome.get("status") not in {"proved", "failed", "proved_with_replay_gaps"}
                or isinstance(outcome.get("returncode"), bool)
                or not isinstance(outcome.get("returncode"), int)
                or outcome.get("returncode") != (0 if outcome["status"] == "proved" else 1)):
            raise RuntimeError(f"P-01 expected status is incomplete or inconsistent for {name}")
        semantic = row.get("semantic_expectations")
        if not isinstance(semantic, dict):
            raise RuntimeError(f"P-01 semantic expectations are missing for {name}")
        if any(isinstance(semantic.get(key), bool) or not isinstance(semantic.get(key), int)
               or semantic[key] < 0 for key in semantic_counts):
            raise RuntimeError(f"P-01 semantic counts are incomplete for {name}")
        ids = semantic.get("obligation_ids")
        details = semantic.get("obligation_details")
        assumption_details = semantic.get("trusted_assumption_details")
        inventory_complete = semantic.get("obligation_inventory_complete")
        if (not isinstance(ids, list) or any(isinstance(item, bool) or not isinstance(item, int)
                                             for item in ids)
                or len(set(ids)) != len(ids)
                or not isinstance(details, list)
                or not isinstance(assumption_details, list)
                or not isinstance(inventory_complete, bool)):
            raise RuntimeError(f"P-01 obligation/assumption inventory is incomplete for {name}")
        if (len(details) != len(ids)
                or (inventory_complete and len(ids) != semantic["obligation_count"])
                or [item.get("id") if isinstance(item, dict) else None for item in details] != ids
                or any(isinstance(item, bool) or not isinstance(item, int)
                       for item in (detail.get("id") for detail in details if isinstance(detail, dict)))
                or semantic["trusted_assumptions"] != len(assumption_details)):
            raise RuntimeError(f"P-01 obligation/assumption identity disagrees for {name}")
        if any(not isinstance(item, dict)
               or isinstance(item.get("id"), bool) or not isinstance(item.get("id"), int)
               or not isinstance(item.get("function"), str)
               or isinstance(item.get("line"), bool) or not isinstance(item.get("line"), int)
               or not isinstance(item.get("rule"), str)
               or item.get("result") not in ("proved", "unproven")
               for item in details):
            raise RuntimeError(f"P-01 obligation row is malformed for {name}")
        if (semantic["proven"] + semantic["unproven"] != semantic["obligation_count"]
                or semantic["failed"] > semantic["unproven"]
                or semantic["obligation_detail_proven"] + semantic["obligation_detail_unproven"] != len(details)
                or (inventory_complete and (semantic["obligation_detail_proven"] != semantic["proven"]
                                            or semantic["obligation_detail_unproven"] != semantic["unproven"]))
                or semantic["proof_certificates"] != semantic["replay_certificates"]
                or semantic["replay_certificates"] != semantic["replayed"] + semantic["replay_gaps"]):
            raise RuntimeError(f"P-01 semantic/replay totals are inconsistent for {name}")
        if (sum(item.get("result") == "proved" for item in details if isinstance(item, dict))
                != semantic["obligation_detail_proven"]
                or sum(item.get("result") == "unproven" for item in details if isinstance(item, dict))
                != semantic["obligation_detail_unproven"]
                or any(not isinstance(item, dict) or item.get("result") not in {"proved", "unproven"}
                       for item in details)):
            raise RuntimeError(f"P-01 obligation results disagree with totals for {name}")
    validate_workload_membership(payload, fixtures)
    return fixtures


def validate_workload_membership(manifest: dict, fixtures: dict) -> None:
    """Require a closed, one-to-one identity map from fixture rows to workload records."""
    workloads = manifest.get("workloads")
    if not isinstance(workloads, dict) or not workloads:
        raise RuntimeError("P-01 workload identity inventory is missing")

    members_seen: dict[str, str] = {}
    for workload_name, workload in workloads.items():
        if not isinstance(workload_name, str) or not workload_name or not isinstance(workload, dict):
            raise RuntimeError("P-01 workload identity record is malformed")
        members = workload.get("members")
        if (not isinstance(members, list) or not members
                or any(not isinstance(member, str) or not member for member in members)
                or len(set(members)) != len(members)):
            raise RuntimeError(f"P-01 workload identity members are missing or duplicated for {workload_name}")
        if not isinstance(workload.get("shape"), str) or not workload["shape"]:
            raise RuntimeError(f"P-01 workload shape identity is missing for {workload_name}")
        if not isinstance(workload.get("source_relation"), str) or not workload["source_relation"]:
            raise RuntimeError(f"P-01 workload source identity is missing for {workload_name}")
        for member in members:
            if member not in fixtures:
                raise RuntimeError(f"P-01 workload {workload_name} names missing fixture {member}")
            if member in members_seen:
                raise RuntimeError(f"P-01 fixture {member} belongs to multiple workload identities")
            if fixtures[member].get("workload") != workload_name:
                raise RuntimeError(f"P-01 fixture {member} disagrees with workload identity {workload_name}")
            members_seen[member] = workload_name

    if set(members_seen) != set(fixtures):
        missing = sorted(set(fixtures) - set(members_seen))
        extra = sorted(set(members_seen) - set(fixtures))
        raise RuntimeError(f"P-01 workload identity inventory does not cover fixtures; missing={missing}, extra={extra}")


EXPECTED_OUTCOMES = {name: row["expected_outcome"]
                     for name, row in load_sentinel_manifest().items()}
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
MEASURED_PHASE_TIMINGS = (
    "proof_cli_invocation_wall",
    "proof_cli_child_cpu",
    "baseline_harness_json_decode",
)


def identity(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def source_line_count(path: Path) -> int:
    data = path.read_bytes()
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def validate_workload_identities(sentinels: dict) -> dict:
    """Bind every manifest row to the fixed name/path table and current fixture bytes."""
    if set(sentinels) != {name for name, _ in FIXTURES}:
        raise RuntimeError("P-01 fixtures do not match the versioned sentinel manifest")
    fixture_ids = {name: identity(path) for name, path in FIXTURES}
    for name, path in FIXTURES:
        sentinel = sentinels[name]
        if sentinel.get("path") != str(path.relative_to(ROOT)):
            raise RuntimeError(f"P-01 sentinel path changed for {name}")
        if (sentinel.get("sha256") != fixture_ids[name]["sha256"]
                or sentinel.get("size_bytes") != fixture_ids[name]["size_bytes"]
                or sentinel.get("source_lines") != source_line_count(path)):
            raise RuntimeError(f"P-01 workload identity changed for {name}; review and version the sentinel")
    return fixture_ids


def build_identity(binary: Path) -> dict:
    """Read and verify the adjacent build manifest so measurements name the exact toolchain."""
    manifest_path = Path(str(binary) + ".manifest.json")
    digest_path = Path(str(manifest_path) + ".sha256")
    if not manifest_path.is_file() or not digest_path.is_file():
        return {"available": False, "reason": "build manifest or checksum is missing"}
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    recorded_sha256 = digest_path.read_text(encoding="ascii").strip()
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"build manifest is invalid JSON: {error}") from error
    binary_sha256 = identity(binary)["sha256"]
    if recorded_sha256 != manifest_sha256:
        raise RuntimeError("build manifest checksum does not match its sidecar")
    if manifest.get("binary", {}).get("sha256") != binary_sha256:
        raise RuntimeError("build manifest does not describe the selected proof binary")
    proof = manifest.get("proof")
    frontend = manifest.get("frontend")
    compiler = manifest.get("compiler")
    runtime = manifest.get("runtime")
    if not isinstance(proof, dict) or not proof.get("source_tree_sha256"):
        raise RuntimeError("build manifest is missing the proof source identity")
    if not isinstance(frontend, dict) or not frontend.get("revision") or not frontend.get("tree"):
        raise RuntimeError("build manifest is missing the frontend revision/tree identity")
    if not isinstance(compiler, dict) or not isinstance(compiler.get("product"), dict) \
            or not compiler["product"].get("sha256"):
        raise RuntimeError("build manifest is missing the compiler product identity")
    if not isinstance(runtime, dict) or not runtime.get("sha256"):
        raise RuntimeError("build manifest is missing the runtime identity")
    for key in ("target", "optimization", "compile_mode"):
        if not manifest.get(key):
            raise RuntimeError(f"build manifest is missing {key} identity")
    return {"available": True, "path": str(manifest_path), "sha256": manifest_sha256,
            "build_identity": manifest.get("build_identity"),
            "proof": proof, "frontend": frontend,
            "compiler": compiler, "runtime": runtime,
            "target": manifest.get("target"), "optimization": manifest.get("optimization"),
            "compile_mode": manifest.get("compile_mode")}


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
    rounds = getattr(args, "rounds", 1)
    warmup_runs = getattr(args, "warmup_runs", 0)
    if rounds <= 0 or warmup_runs < 0:
        raise RuntimeError("rounds must be positive and warm-up runs cannot be negative")
    sentinels = load_sentinel_manifest()
    fixture_ids = validate_workload_identities(sentinels)
    manifest = json.loads(SENTINEL_MANIFEST.read_text(encoding="utf-8"))
    for workload_name, workload in manifest.get("workloads", {}).items():
        members = workload.get("members", [])
        if not any(member in sentinels for member in members):
            continue
        if len(members) != 2 or any(member not in sentinels for member in members):
            raise RuntimeError(f"P-01 workload {workload_name} must name exactly two pinned fixtures")
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
                "source_imported_bytes": "expanded-source-byte-count-available",
                "source_file_count": "source-map-file-count-available",
                "token_count": "available-in-cli-before-token-arena-release",
                "top_level_declaration_count": "serialized-declaration-count",
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
