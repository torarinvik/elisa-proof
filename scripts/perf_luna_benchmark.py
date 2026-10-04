#!/usr/bin/env python3
"""Bounded, deterministic A/B benchmark for proof reports and portable replay.

Both binaries are supplied by the caller. This script never builds or installs software.
Proof JSON and portable replay results are compared exactly before measurements are emitted.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import resource
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "elisa-proof-perf-luna-v1"
FIXTURES = (
    ("accept", ROOT / "examples" / "perf_luna_accept.elisa", 0, "proved"),
    ("refusal", ROOT / "examples" / "perf_luna_refusal.elisa", 1, "failed"),
    ("symbolic_quantifier", ROOT / "examples" / "symbolic_quantifier.elisa", 0, "proved"),
    ("rejected_symbolic_quantifier", ROOT / "examples" / "rejected_symbolic_quantifier.elisa", 1, "failed"),
    ("congruence", ROOT / "examples" / "congruence.elisa", 0, "proved"),
    ("rejected_congruence", ROOT / "examples" / "rejected_congruence.elisa", 1, "failed"),
)
MUST_REMAIN_UNPROVEN = {
    "refusal": ("perf_luna_must_remain_open",),
    "rejected_symbolic_quantifier": (
        "bubble_pass_strict", "congruence_other_index", "congruence_other_container",
        "negated_not_strict", "negated_wrong_direction", "guard_not_refuted",
        "guard_mentions_binder", "guard_not_negated", "instance_outside",
        "lower_missing_point", "lower_two_short", "narrow_keeps_write",
        "binding_other_value", "subscript_unequal", "subscript_other_container",
        "alias_outside", "alias_other_container", "alias_carried_outside",
    ),
}
MUST_DECLINE_QUANTIFIER_CERTIFICATE = {
    "rejected_symbolic_quantifier": (
        "off_by_one", "wrong_lower", "other_body", "shadow", "weaken_wrong_way",
        "weaken_wider", "weaken_grown_missing_point", "element_not_strict",
    ),
}
MUST_HAVE_FINDINGS = {
    "rejected_congruence": (
        "disequality_premise", "order_premise", "disjunctive_premise",
        "unrelated_operand", "distinct_former", "struct_equality_premise",
        "local_struct_equality_premise", "constructed_aggregate",
        "cross_width", "wrapping_operand",
    ),
}
MUST_PROVE = {
    # Pure identity calls are reduced through verified summaries, not a new
    # trusted call-congruence former. Their remaining goal is the premise a == b.
    "rejected_congruence": ("indexed_element", "call_congruence"),
}
MUST_BE_INADMISSIBLE = {"rejected_symbolic_quantifier"}
MAX_ROUNDS = 9
MAX_TIMEOUT = 300


def file_identity(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def require_unchanged_inputs(identities: dict[Path, dict]) -> None:
    for path, identity in identities.items():
        if file_identity(path) != identity:
            raise RuntimeError(f"benchmark input changed during measurement: {path}")


def measured_child(command: list[str]) -> int:
    """Run one tool and emit its exact streams plus per-child process metrics.

    The outer watchdog owns the process group and its deadline, so this layer deliberately
    has no independent timeout that could orphan descendants.
    """
    started = time.perf_counter()
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False)
    stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    elapsed = time.perf_counter() - started
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    # macOS reports bytes; Linux and the supported Vast Linux hosts report KiB.
    peak_kib = peak / 1024 if sys.platform == "darwin" else peak
    payload = {
        "returncode": returncode,
        "wall_seconds": elapsed,
        "peak_rss_kib": peak_kib,
        "stdout": base64.b64encode(stdout).decode("ascii"),
        "stderr": base64.b64encode(stderr).decode("ascii"),
    }
    sys.stdout.write(json.dumps(payload, separators=(",", ":")))
    return 0


def invoke(binary: Path, arguments: list[str], timeout: int) -> dict:
    command = [str(binary), *arguments]
    wrapper = [sys.executable, str(Path(__file__).resolve()), "_measure",
               json.dumps(command, separators=(",", ":"))]
    run = run_wrapper(wrapper, timeout)
    if run.returncode != 0:
        raise RuntimeError(f"measurement wrapper failed ({run.returncode}): {run.stderr.strip()}")
    try:
        result = json.loads(run.stdout)
        result["stdout"] = base64.b64decode(result["stdout"], validate=True)
        result["stderr"] = base64.b64decode(result["stderr"], validate=True)
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid measurement wrapper response: {run.stdout[:300]!r}") from error
    return result


def run_wrapper(wrapper: list[str], timeout: float) -> subprocess.CompletedProcess:
    """Run a measurement wrapper in its own process group and reap it on timeout."""
    process = subprocess.Popen(wrapper, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        raise RuntimeError(f"measurement wrapper timed out after {timeout}s: {stderr.strip()}") from error
    return subprocess.CompletedProcess(wrapper, process.returncode, stdout, stderr)


def process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                               capture_output=True, text=True, check=False).stdout.strip()
    except OSError:
        return True
    return bool(state) and not state.startswith("Z")


def self_test_process_group_cleanup() -> None:
    """Check a normal measured command and prove timeout cleanup kills its process tree."""
    ordinary_command = [sys.executable, str(Path(__file__).resolve()), "_measure",
                        json.dumps([sys.executable, "-c", "print('ordinary')"],
                                   separators=(",", ":"))]
    ordinary = run_wrapper(ordinary_command, 5)
    if ordinary.returncode != 0:
        raise RuntimeError(f"ordinary measurement failed: {ordinary.stderr.strip()}")
    try:
        measured = json.loads(ordinary.stdout)
        ordinary_stdout = base64.b64decode(measured["stdout"], validate=True)
    except (ValueError, KeyError) as error:
        raise RuntimeError("ordinary measurement returned invalid output") from error
    if measured.get("returncode") != 0 or ordinary_stdout != b"ordinary\n":
        raise RuntimeError("ordinary measurement did not preserve its successful command output")

    with tempfile.TemporaryDirectory(prefix="elisa-perf-luna-self-test-") as temporary:
        directory = Path(temporary)
        stable = directory / "identity-control"
        stable.write_bytes(b"stable input")
        identities = {stable: file_identity(stable)}
        if identities[stable] != {"sha256": hashlib.sha256(b"stable input").hexdigest(),
                                  "size_bytes": len(b"stable input")}:
            raise RuntimeError("benchmark input identity is incorrect")
        require_unchanged_inputs(identities)
        stable.write_bytes(b"mutated input")
        try:
            require_unchanged_inputs(identities)
        except RuntimeError as error:
            if "input changed" not in str(error):
                raise
        else:
            raise RuntimeError("benchmark input mutation was not refused")
        target = directory / "fake-proof"
        pid_file = directory / "child.pid"
        target.write_text(
            "#!/usr/bin/env python3\n"
            "import subprocess, sys, time\n"
            "child = subprocess.Popen(['sleep', '60'])\n"
            "open(sys.argv[1], 'w').write(str(child.pid))\n"
            "time.sleep(60)\n",
            encoding="utf-8",
        )
        target.chmod(0o755)
        command = [sys.executable, str(Path(__file__).resolve()), "_measure",
                   json.dumps([str(target), str(pid_file)], separators=(",", ":"))]
        try:
            run_wrapper(command, 2)
        except RuntimeError as error:
            if "timed out" not in str(error):
                raise
        else:
            raise RuntimeError("watchdog did not time out the sleeping fake executable")
        if not pid_file.exists():
            raise RuntimeError("fake executable did not start its child before timeout")
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 3
        while process_is_running(child_pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        if process_is_running(child_pid):
            raise RuntimeError(f"target child {child_pid} survived process-group cleanup")


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
    goals = report.get("goals", [])
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
    times = [sample["wall_seconds"] for sample in samples]
    rss = [sample["peak_rss_kib"] for sample in samples]
    return {
        "rounds": len(samples),
        "median_wall_seconds": round(statistics.median(times), 6),
        "peak_rss_kib": int(max(rss)),
    }


def run(args: argparse.Namespace) -> dict:
    binaries = {
        "baseline": (args.baseline_proof.resolve(), args.baseline_replay.resolve()),
        "candidate": (args.candidate_proof.resolve(), args.candidate_replay.resolve()),
    }
    for label, pair in binaries.items():
        for binary in pair:
            if not binary.is_file() or not os.access(binary, os.X_OK):
                raise RuntimeError(f"{label} executable is missing or not executable: {binary}")

    identities = {path: file_identity(path) for pair in binaries.values() for path in pair}
    identities.update({source: file_identity(source) for _, source, _, _ in FIXTURES})

    entries = []
    with tempfile.TemporaryDirectory(prefix="elisa-proof-perf-luna-") as temporary:
        scratch = Path(temporary)
        for fixture, source, proof_exit, proof_status in FIXTURES:
            run_outputs = {}
            for variant, (proof_binary, replay_binary) in binaries.items():
                outputs = {"proof": [], "export": [], "replay": []}
                package_path = scratch / f"{variant}-{fixture}.json"
                for _ in range(args.rounds):
                    proof = invoke(proof_binary, ["--json", str(source)], args.timeout)
                    check_exit(proof, proof_exit, f"{variant}/{fixture}/proof")
                    proof_report(proof, proof_status, f"{variant}/{fixture}/proof",
                                 MUST_REMAIN_UNPROVEN.get(fixture, ()),
                                 MUST_PROVE.get(fixture, ()),
                                 MUST_HAVE_FINDINGS.get(fixture, ()))
                    report = json.loads(proof["stdout"])
                    declined = set(MUST_DECLINE_QUANTIFIER_CERTIFICATE.get(fixture, ()))
                    if any(certificate.get("name") in declined
                           and certificate.get("rule", "").startswith("quantifier")
                           for certificate in report.get("certificates", [])):
                        raise RuntimeError(f"{variant}/{fixture}: adversarial quantifier certificate admitted")
                    outputs["proof"].append(proof)

                    export = invoke(proof_binary, ["--package", str(source)], args.timeout)
                    # Export exit status reports source admissibility. Refused sources may
                    # still produce a valid package envelope, but never carry theorems.
                    try:
                        package = json.loads(export["stdout"])
                    except (ValueError, KeyError) as error:
                        raise RuntimeError(f"{variant}/{fixture}: invalid package export") from error
                    if not isinstance(package, dict):
                        raise RuntimeError(f"{variant}/{fixture}: package has an invalid top-level schema")
                    source_info = package.get("source", {})
                    if not isinstance(source_info, dict):
                        raise RuntimeError(f"{variant}/{fixture}: package source record is missing")
                    admissible = source_info.get("admissible")
                    if (package.get("format") != "elisa-proof-package-v1"
                            or type(admissible) is not bool
                            or source_info.get("authenticated") is not False):
                        raise RuntimeError(f"{variant}/{fixture}: invalid package schema or admissibility flag")
                    if fixture in MUST_BE_INADMISSIBLE and admissible:
                        raise RuntimeError(f"{variant}/{fixture}: expected source-admissibility refusal")
                    if export["returncode"] != (0 if admissible else 1):
                        raise RuntimeError(f"{variant}/{fixture}: export exit disagrees with source admissibility")
                    theorems = package.get("theorems")
                    if not isinstance(theorems, list):
                        raise RuntimeError(f"{variant}/{fixture}: package theorem list is missing")
                    if not admissible and theorems:
                        raise RuntimeError(f"{variant}/{fixture}: inadmissible source exported theorems")
                    expected_replay = "replayed" if theorems else "rejected"
                    expected_reason = None if theorems else (
                        "source-inadmissible" if not admissible else "no-theorems")
                    replay_exit = 0 if theorems else 1
                    package_path.write_bytes(export["stdout"])
                    outputs["export"].append(export)

                    replay = invoke(replay_binary, [str(package_path)], args.timeout)
                    check_exit(replay, replay_exit, f"{variant}/{fixture}/replay")
                    replay_result(replay, expected_replay, expected_reason,
                                  f"{variant}/{fixture}/replay")
                    outputs["replay"].append(replay)
                run_outputs[variant] = outputs

            baseline = run_outputs["baseline"]
            candidate = run_outputs["candidate"]
            for phase in ("proof", "export", "replay"):
                reference = (baseline[phase][0]["returncode"], baseline[phase][0]["stdout"],
                             baseline[phase][0]["stderr"])
                if any((item["returncode"], item["stdout"], item["stderr"]) != reference
                       for item in baseline[phase] + candidate[phase]):
                    raise RuntimeError(f"{fixture}/{phase}: outputs differ between rounds or binaries")

            entries.append({
                "fixture": fixture,
                "source": {"path": str(source), **identities[source]},
                "proof": {variant: record_measurements(data["proof"])
                          for variant, data in run_outputs.items()},
                "package_export": {variant: record_measurements(data["export"])
                                   for variant, data in run_outputs.items()},
                "standalone_replay": {variant: record_measurements(data["replay"])
                                      for variant, data in run_outputs.items()},
                "outputs_identical": True,
            })

    require_unchanged_inputs(identities)
    return {
        "schema": SCHEMA,
        "comparison": "exact-stdout-bytes",
        "rounds": args.rounds,
        "timeout_seconds": args.timeout,
        "host": {"platform": sys.platform, "machine": platform.machine(),
                 "python": platform.python_version()},
        "binaries": {label: {"proof": str(pair[0]), "replay": str(pair[1]),
                             "proof_identity": identities[pair[0]],
                             "replay_identity": identities[pair[1]]}
                     for label, pair in binaries.items()},
        "fixtures": entries,
    }


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "_measure":
        try:
            command = json.loads(sys.argv[2])
            if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
                return 2
            return measured_child(command)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"measurement failed: {error}", file=sys.stderr)
            return 2

    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        try:
            self_test_process_group_cleanup()
        except (OSError, RuntimeError) as error:
            print(f"perf_luna_benchmark self-test failed: {error}", file=sys.stderr)
            return 1
        print("perf_luna_benchmark input identity and process cleanup self-tests passed")
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-proof", type=Path, required=True)
    parser.add_argument("--candidate-proof", type=Path, required=True)
    parser.add_argument("--baseline-replay", type=Path, required=True)
    parser.add_argument("--candidate-replay", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", type=Path, help="write the JSON report here; stdout by default")
    args = parser.parse_args()
    if not 1 <= args.rounds <= MAX_ROUNDS:
        parser.error(f"--rounds must be between 1 and {MAX_ROUNDS}")
    if not 1 <= args.timeout <= MAX_TIMEOUT:
        parser.error(f"--timeout must be between 1 and {MAX_TIMEOUT} seconds")
    try:
        report = run(args)
    except (OSError, RuntimeError) as error:
        print(f"perf_luna_benchmark: {error}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
