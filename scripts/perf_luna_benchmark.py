#!/usr/bin/env python3
"""Bounded, deterministic A/B benchmark for proof reports and portable replay.

Both binaries are supplied by the caller. This script never builds or installs software.
Proof JSON and portable replay results are compared exactly before measurements are emitted.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from perf_build_provenance import (
    file_identity,
    manifest_self_test,
    read_build_manifest,
    require_compatible_products,
    shared_product_context,
)
from perf_luna_benchmark_process import (
    require_unchanged_inputs,
    run_wrapper,
    self_test_process_group_cleanup,
)
from perf_luna_benchmark_validation import (
    check_exit,
    measurement_self_test,
    proof_report,
    record_measurements,
    replay_result,
    semantic_workload_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "elisa-proof-perf-luna-v3"
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
MAX_WARMUP_ROUNDS = 3


def require_unchanged_inputs(identities: dict[Path, dict]) -> None:
    for path, identity in identities.items():
        if file_identity(path) != identity:
            raise RuntimeError(f"benchmark input changed during measurement: {path}")


def verify_build_snapshot(binaries: dict, manifests: dict, identities: dict[Path, dict]) -> None:
    """Bind parsed manifest contents to the exact files measured by this run."""
    for label, pair in binaries.items():
        for role, binary in zip(("proof", "replay"), pair):
            current = read_build_manifest(binary, f"{label}/{role}")
            if current != manifests[label][role]:
                raise RuntimeError(f"{label}/{role} build manifest changed while creating benchmark snapshot")
    require_unchanged_inputs(identities)


def measured_child(command: list[str]) -> int:
    """Run one tool and emit its exact streams plus per-child process metrics.

    The outer watchdog owns the process group and its deadline, so this layer deliberately
    has no independent timeout that could orphan descendants.
    """
    started = time.perf_counter()
    cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False)
    stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    elapsed = time.perf_counter() - started
    cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    peak = cpu_after.ru_maxrss
    # macOS reports bytes; Linux and the supported Vast Linux hosts report KiB.
    peak_kib = peak / 1024 if sys.platform == "darwin" else peak
    payload = {
        "returncode": returncode,
        "wall_seconds": elapsed,
        "user_cpu_seconds": max(0.0, cpu_after.ru_utime - cpu_before.ru_utime),
        "system_cpu_seconds": max(0.0, cpu_after.ru_stime - cpu_before.ru_stime),
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


def invoke_for_side(binary: Path, arguments: list[str], timeout: int,
                    side: str, fixture: str, phase: str) -> dict:
    """Make watchdog censoring explicit and attributable; censored runs have no result."""
    try:
        return invoke(binary, arguments, timeout)
    except RuntimeError as error:
        if "timed out" in str(error):
            raise RuntimeError(
                f"{side}/{fixture}/{phase}: classification=timeout; censored=true; "
                "speedup=not-reported"
            ) from error
        raise


def run(args: argparse.Namespace) -> dict:
    binaries = {
        "baseline": (args.baseline_proof.resolve(), args.baseline_replay.resolve()),
        "candidate": (args.candidate_proof.resolve(), args.candidate_replay.resolve()),
    }
    for label, pair in binaries.items():
        for binary in pair:
            if not binary.is_file() or not os.access(binary, os.X_OK):
                raise RuntimeError(f"{label} executable is missing or not executable: {binary}")

    product_contexts = {}
    product_manifests = {}
    for label, (proof_binary, replay_binary) in binaries.items():
        proof_manifest = read_build_manifest(proof_binary, f"{label}/proof")
        replay_manifest = read_build_manifest(replay_binary, f"{label}/replay")
        product_manifests[label] = {"proof": proof_manifest, "replay": replay_manifest}
        product_contexts[label] = require_compatible_products(
            proof_manifest, replay_manifest, label
        )
    toolchain_keys = tuple(key for key in product_contexts["baseline"]
                           if not key.startswith("proof."))
    toolchain_differences = [key for key in toolchain_keys
                             if product_contexts["baseline"][key]
                             != product_contexts["candidate"][key]]
    if toolchain_differences:
        raise RuntimeError(
            "baseline/candidate builds use different frontends or toolchains: "
            f"{toolchain_differences}"
        )

    manifest_paths = [Path(str(binary) + suffix)
                      for pair in binaries.values() for binary in pair
                      for suffix in (".manifest.json", ".manifest.json.sha256")]
    identities = {path: file_identity(path) for pair in binaries.values() for path in pair}
    identities.update({path: file_identity(path) for path in manifest_paths})
    identities.update({source: file_identity(source) for _, source, _, _ in FIXTURES})
    verify_build_snapshot(binaries, product_manifests, identities)

    entries = []
    with tempfile.TemporaryDirectory(prefix="elisa-proof-perf-luna-") as temporary:
        scratch = Path(temporary)
        for fixture, source, proof_exit, proof_status in FIXTURES:
            run_outputs = {variant: {"proof": [], "export": [], "replay": []}
                           for variant in binaries}
            semantic_metrics = {}
            total_rounds = args.warmup_rounds + args.rounds
            for round_index in range(total_rounds):
                is_warmup = round_index < args.warmup_rounds
                variants = list(binaries)
                if round_index % 2:
                    variants.reverse()
                for variant in variants:
                    proof_binary, replay_binary = binaries[variant]
                    outputs = run_outputs[variant]
                    package_path = scratch / f"{variant}-{fixture}.json"
                    proof = invoke_for_side(proof_binary, ["--json", str(source)], args.timeout,
                                            variant, fixture, "proof")
                    check_exit(proof, proof_exit, f"{variant}/{fixture}/proof")
                    proof_report(proof, proof_status, f"{variant}/{fixture}/proof",
                                 MUST_REMAIN_UNPROVEN.get(fixture, ()),
                                 MUST_PROVE.get(fixture, ()),
                                 MUST_HAVE_FINDINGS.get(fixture, ()))
                    report = json.loads(proof["stdout"])
                    semantic_metrics[variant] = semantic_workload_metrics(
                        proof, report, f"{variant}/{fixture}/proof"
                    )
                    declined = set(MUST_DECLINE_QUANTIFIER_CERTIFICATE.get(fixture, ()))
                    if any(certificate.get("name") in declined
                           and certificate.get("rule", "").startswith("quantifier")
                           for certificate in report.get("certificates", [])):
                        raise RuntimeError(f"{variant}/{fixture}: adversarial quantifier certificate admitted")
                    if not is_warmup:
                        outputs["proof"].append(proof)

                    export = invoke_for_side(proof_binary, ["--package", str(source)], args.timeout,
                                             variant, fixture, "export")
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
                    if not is_warmup:
                        outputs["export"].append(export)

                    replay = invoke_for_side(replay_binary, [str(package_path)], args.timeout,
                                             variant, fixture, "replay")
                    check_exit(replay, replay_exit, f"{variant}/{fixture}/replay")
                    replay_result(replay, expected_replay, expected_reason,
                                  f"{variant}/{fixture}/replay")
                    if not is_warmup:
                        outputs["replay"].append(replay)

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
                "semantic_workload": semantic_metrics,
                "outputs_identical": True,
            })

    require_unchanged_inputs(identities)
    return {
        "schema": SCHEMA,
        "comparison": "exact-stdout-bytes",
        "measurement_order": "alternating-baseline-candidate",
        "wall_percentile_method": "nearest-rank",
        "rounds": args.rounds,
        "warmup_rounds": args.warmup_rounds,
        "timeout_seconds": args.timeout,
        "host": {"platform": sys.platform, "machine": platform.machine(),
                 "python": platform.python_version()},
        "binaries": {label: {"proof": str(pair[0]), "replay": str(pair[1]),
                             "proof_identity": identities[pair[0]],
                             "replay_identity": identities[pair[1]],
                             "proof_manifest_identity": identities[Path(
                                 str(pair[0]) + ".manifest.json")],
                             "replay_manifest_identity": identities[Path(
                                 str(pair[1]) + ".manifest.json")]}
                     for label, pair in binaries.items()},
        "build_context": product_contexts,
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
            self_test_process_group_cleanup(Path(__file__).resolve())
            measurement_self_test()
            manifest_self_test()
        except (OSError, RuntimeError) as error:
            print(f"perf_luna_benchmark self-test failed: {error}", file=sys.stderr)
            return 1
        print("perf_luna_benchmark provenance, metrics, input identity, and process cleanup self-tests passed")
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-proof", type=Path, required=True)
    parser.add_argument("--candidate-proof", type=Path, required=True)
    parser.add_argument("--baseline-replay", type=Path, required=True)
    parser.add_argument("--candidate-replay", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--warmup-rounds", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", type=Path, help="write the JSON report here; stdout by default")
    args = parser.parse_args()
    if not 1 <= args.rounds <= MAX_ROUNDS:
        parser.error(f"--rounds must be between 1 and {MAX_ROUNDS}")
    if not 1 <= args.timeout <= MAX_TIMEOUT:
        parser.error(f"--timeout must be between 1 and {MAX_TIMEOUT} seconds")
    if not 0 <= args.warmup_rounds <= MAX_WARMUP_ROUNDS:
        parser.error(f"--warmup-rounds must be between 0 and {MAX_WARMUP_ROUNDS}")
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
