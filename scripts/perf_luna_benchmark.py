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
import sys
import tempfile
from pathlib import Path

from perf_build_provenance import (
    file_identity,
    manifest_self_test,
    read_build_manifest,
    require_clean_toolchain,
    require_compatible_products,
    shared_product_context,
    verify_build_artifacts,
    verify_proof_source,
)
from perf_luna_benchmark_process import (
    measured_child,
    require_unchanged_inputs,
    run_wrapper,
    self_test_process_group_cleanup,
)
from perf_luna_benchmark_evidence import semantic_outcome_projection
from perf_luna_benchmark_validation import (
    check_exit,
    measurement_self_test,
    proof_report,
    record_measurements,
    replay_result,
    semantic_workload_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "elisa-proof-perf-luna-v4"
FIXTURES = (
    ("accept", ROOT / "examples" / "perf_luna_accept.elisa", 0, "proved"),
    ("refusal", ROOT / "examples" / "perf_luna_refusal.elisa", 1, "failed"),
    ("symbolic_quantifier", ROOT / "examples" / "symbolic_quantifier.elisa", 0, "proved"),
    ("rejected_symbolic_quantifier", ROOT / "examples" / "rejected_symbolic_quantifier.elisa", 1, "failed"),
    ("congruence", ROOT / "examples" / "congruence.elisa", 0, "proved"),
    ("rejected_congruence", ROOT / "examples" / "rejected_congruence.elisa", 1, "failed"),
)
FIXTURE_SHA256 = {
    "accept": "b98bc4c879e7ca4279515ade0c248d125f9323a1f3e01f9bed389fc9a818354b",
    "refusal": "5bb1c84d7baf95c9853e448062184a3427b298d80b205ed7cd9ac8032a7cd454",
    "symbolic_quantifier": "eb8ea811bdf07e0796eeecc929a0b007bb44813724214e8bbc952a65325e0e9e",
    "rejected_symbolic_quantifier": "5c1990bafd783178ad4bc66916fa35c16b8670a7dc30d8443f077b161cd3b352",
    "congruence": "99b0a7a7712de6c427ed84eedfb4853e5639c83fb35c224a6d14c9c08bdaebca",
    "rejected_congruence": "8cd9f33f34c9fa124aa9bad5740a3619000a71dcab706274f9d1c7f9f1e6e534",
}
FIXTURE_BY_NAME = {name: (name, source, exit_code, status)
                   for name, source, exit_code, status in FIXTURES}
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
            verify_build_artifacts(current, f"{label}/{role}")
    require_unchanged_inputs(identities)


def semantic_projection(report: dict) -> dict:
    """Fields that describe proof meaning/trust, excluding runtime measurements."""
    required = ("status", "verification_state", "summary", "declaration_details",
                "functions", "goals", "findings", "certificates", "replay", "trust")
    missing = [field for field in required if field not in report]
    if missing:
        raise RuntimeError(f"proof report lacks semantic/trust fields: {missing}")
    return {field: report[field] for field in required}


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def package_projection(package: dict) -> dict:
    required = ("format", "source", "theorems")
    if any(field not in package for field in required):
        raise RuntimeError("package export lacks source or theorem inventory")
    return {field: package[field] for field in required}


def output_projection(phase: str, output: bytes) -> bytes:
    try:
        decoded = json.loads(output)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{phase} emitted invalid JSON during measurement") from error
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{phase} emitted a non-object JSON result")
    if phase == "proof":
        return canonical_json(semantic_projection(decoded))
    if phase == "export":
        return canonical_json(package_projection(decoded))
    if phase == "replay":
        return canonical_json(decoded)
    raise RuntimeError(f"unknown benchmark phase: {phase}")


def preflight_semantics(binaries: dict, fixtures: tuple, timeout: int) -> dict:
    """Run untimed paired checks; no measurement starts until semantics and trust match."""
    results = {}
    with tempfile.TemporaryDirectory(prefix="elisa-proof-perf-preflight-") as temporary:
        scratch = Path(temporary)
        for fixture, source, expected_exit, expected_status in fixtures:
            per_variant = {}
            for variant in ("baseline", "candidate"):
                proof_binary, replay_binary = binaries[variant]
                proof = invoke_for_side(proof_binary, ["--json", str(source)], timeout,
                                        variant, fixture, "preflight-proof")
                check_exit(proof, expected_exit, f"{variant}/{fixture}/preflight-proof")
                report = proof_report(proof, expected_status,
                                      f"{variant}/{fixture}/preflight-proof",
                                      MUST_REMAIN_UNPROVEN.get(fixture, ()),
                                      MUST_PROVE.get(fixture, ()),
                                      MUST_HAVE_FINDINGS.get(fixture, ()))
                proof_semantics = semantic_projection(report)
                semantic_workload_metrics(proof, report, f"{variant}/{fixture}/preflight-proof")

                export = invoke_for_side(proof_binary, ["--package", str(source)], timeout,
                                         variant, fixture, "preflight-export")
                try:
                    package = json.loads(export["stdout"])
                except (ValueError, KeyError) as error:
                    raise RuntimeError(f"{variant}/{fixture}: invalid preflight package") from error
                if not isinstance(package, dict):
                    raise RuntimeError(f"{variant}/{fixture}: package export is not an object")
                projected_package = package_projection(package)
                source_info = package.get("source", {})
                admissible = source_info.get("admissible") if isinstance(source_info, dict) else None
                if type(admissible) is not bool:
                    raise RuntimeError(f"{variant}/{fixture}: package admissibility is missing")
                if export["returncode"] != (0 if admissible else 1):
                    raise RuntimeError(f"{variant}/{fixture}: export exit disagrees with admissibility")
                package_path = scratch / f"{variant}-{fixture}.json"
                package_path.write_bytes(export["stdout"])
                theorem_count = package.get("theorems")
                if not isinstance(theorem_count, list):
                    raise RuntimeError(f"{variant}/{fixture}: theorem inventory is not an array")
                if fixture in MUST_BE_INADMISSIBLE and admissible:
                    raise RuntimeError(f"{variant}/{fixture}: source should be inadmissible")
                if not admissible and theorem_count:
                    raise RuntimeError(f"{variant}/{fixture}: inadmissible source exported theorems")
                replay_exit = 0 if theorem_count else 1
                replay = invoke_for_side(replay_binary, [str(package_path)], timeout,
                                         variant, fixture, "preflight-replay")
                check_exit(replay, replay_exit, f"{variant}/{fixture}/preflight-replay")
                replay_data = replay_result(
                    replay, "replayed" if theorem_count else "rejected",
                    None if theorem_count else ("source-inadmissible" if not admissible
                                                 else "no-theorems"),
                    f"{variant}/{fixture}/preflight-replay")
                per_variant[variant] = {
                    "proof": proof_semantics,
                    "obligations": proof_semantics["goals"],
                    "trust_roots": proof_semantics["trust"],
                    "package": projected_package,
                    "replay": replay_data,
                }
            if canonical_json(per_variant["baseline"]) != canonical_json(per_variant["candidate"]):
                raise RuntimeError(
                    f"{fixture}: proof semantics, obligation inventory, trust roots, "
                    "package or replay differ; timing refused"
                )
            results[fixture] = "matched-before-timing"
    return results


def censored_failure_report(error: RuntimeError, args: argparse.Namespace | None = None) -> dict | None:
    message = str(error)
    if "censored=true" not in message:
        return None
    report = {
        "schema": SCHEMA,
        "status": "censored",
        "timing_valid": False,
        "speedup": "not-reported",
        "censored_failures": [{"message": message, "censored": True}],
        "note": "No performance conclusion is available for an incomplete paired run.",
    }
    if args is not None:
        report["requested_comparison"] = {
            label: {
                "proof": str(getattr(args, f"{label}_proof")),
                "replay": str(getattr(args, f"{label}_replay")),
                "source_tree_sha256": getattr(args, f"{label}_source_sha256"),
            }
            for label in ("baseline", "candidate")
        }
        report["rounds_requested"] = args.rounds
        report["timeout_seconds"] = args.timeout
    return report


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
    requested_fixtures = getattr(args, "fixtures", None) or list(FIXTURE_BY_NAME)
    fixtures = tuple(FIXTURE_BY_NAME[name] for name in requested_fixtures)
    if not fixtures:
        raise RuntimeError("at least one benchmark fixture must be selected")
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
    source_snapshots = {}
    for label, (proof_binary, replay_binary) in binaries.items():
        proof_manifest = read_build_manifest(proof_binary, f"{label}/proof")
        replay_manifest = read_build_manifest(replay_binary, f"{label}/replay")
        product_manifests[label] = {"proof": proof_manifest, "replay": replay_manifest}
        verify_build_artifacts(proof_manifest, f"{label}/proof")
        verify_build_artifacts(replay_manifest, f"{label}/replay")
        product_contexts[label] = require_compatible_products(
            proof_manifest, replay_manifest, label
        )
        require_clean_toolchain(product_manifests[label], label)
        source_root = getattr(args, f"{label}_source_root", None)
        source_hash = getattr(args, f"{label}_source_sha256", None)
        if source_root is None or source_hash is None:
            raise RuntimeError(
                f"{label} requires --{label}-source-root and --{label}-source-sha256; "
                "the source tree must be independently verified"
            )
        verify_proof_source(product_manifests[label], source_root, source_hash, label)
        source_snapshots[label] = (source_root, source_hash)
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
    identities.update({source: file_identity(source) for _, source, _, _ in fixtures})
    for name, source, _, _ in fixtures:
        expected_hash = FIXTURE_SHA256.get(name)
        if expected_hash is None or identities[source]["sha256"] != expected_hash:
            raise RuntimeError(f"{name}: workload source hash differs from its reviewed corpus identity")
    verify_build_snapshot(binaries, product_manifests, identities)

    preflight = preflight_semantics(binaries, fixtures, args.timeout)
    verify_build_snapshot(binaries, product_manifests, identities)
    for label, (source_root, source_hash) in source_snapshots.items():
        verify_proof_source(product_manifests[label], source_root, source_hash, label)

    entries = []
    with tempfile.TemporaryDirectory(prefix="elisa-proof-perf-luna-") as temporary:
        scratch = Path(temporary)
        for fixture, source, proof_exit, proof_status in fixtures:
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
                reference = (baseline[phase][0]["returncode"],
                             output_projection(phase, baseline[phase][0]["stdout"]))
                if any((item["returncode"], output_projection(phase, item["stdout"])) != reference
                       for item in baseline[phase] + candidate[phase]):
                    raise RuntimeError(
                        f"{fixture}/{phase}: semantic output differs between rounds or binaries"
                    )

            semantic_digests = {}
            for variant, phases in run_outputs.items():
                semantic_digests[variant] = {}
                for phase in ("proof", "export", "replay"):
                    projection = output_projection(phase, phases[phase][0]["stdout"])
                    semantic_digests[variant][phase] = hashlib.sha256(projection).hexdigest()

            paired_samples = {
                phase: {
                    variant: [
                        {"pair_index": index + 1,
                         **{metric: sample.get(metric) for metric in (
                             "wall_seconds", "user_cpu_seconds", "system_cpu_seconds",
                             "peak_rss_kib")}}
                        for index, sample in enumerate(run_outputs[variant][phase])
                    ]
                    for variant in ("baseline", "candidate")
                }
                for phase in ("proof", "export", "replay")
            }
            semantic_outcomes = {
                variant: semantic_outcome_projection(
                    run_outputs[variant]["proof"][0]["stdout"],
                    run_outputs[variant]["export"][0]["stdout"],
                    run_outputs[variant]["replay"][0]["stdout"],
                )
                for variant in ("baseline", "candidate")
            }

            entries.append({
                "fixture": fixture,
                "expected_status": proof_status,
                "expected_exit": proof_exit,
                "source": {"path": str(source), **identities[source]},
                "proof": {variant: record_measurements(data["proof"])
                          for variant, data in run_outputs.items()},
                "package_export": {variant: record_measurements(data["export"])
                                   for variant, data in run_outputs.items()},
                "standalone_replay": {variant: record_measurements(data["replay"])
                                      for variant, data in run_outputs.items()},
                "semantic_workload": semantic_metrics,
                "semantic_outcomes": semantic_outcomes,
                "semantic_output_sha256": semantic_digests,
                "paired_samples": paired_samples,
                "semantic_outputs_identical": True,
            })

    require_unchanged_inputs(identities)
    for label, (source_root, source_hash) in source_snapshots.items():
        verify_proof_source(product_manifests[label], source_root, source_hash, label)
    return {
        "schema": SCHEMA,
        "comparison": "semantic-json-projection-with-trust-and-replay",
        "interpretation": (
            "same-product reproducibility benchmark; no baseline/candidate optimization "
            "difference and no speedup claim"
            if all(identities[binaries["baseline"][index]]
                   == identities[binaries["candidate"][index]] for index in (0, 1))
            else "paired product comparison; performance interpretation requires multiple samples"
        ),
        "selected_fixtures": [name for name, _, _, _ in fixtures],
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
        "build_manifests": {
            label: {
                role: Path(str(binary) + ".manifest.json").read_text(encoding="utf-8")
                for role, binary in zip(("proof", "replay"), binaries[label])
            }
            for label in binaries
        },
        "build_context": product_contexts,
        "source_tree_sha256": {
            label: getattr(args, f"{label}_source_sha256") for label in binaries
        },
        "semantic_preflight": preflight,
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
    parser.add_argument("--fixture", dest="fixtures", action="append",
                        choices=tuple(FIXTURE_BY_NAME),
                        help="select one or more pinned fixtures (repeatable; default: all)")
    for label in ("baseline", "candidate"):
        parser.add_argument(f"--{label}-source-root", type=Path, required=True,
                            help=f"exact src snapshot used to build {label} products")
        parser.add_argument(f"--{label}-source-sha256", required=True,
                            help=f"independently computed SHA-256 of {label} source root")
    parser.add_argument("--output", type=Path, help="write the JSON report here; stdout by default")
    args = parser.parse_args()
    args.fixtures = args.fixtures or list(FIXTURE_BY_NAME)
    if not 1 <= args.rounds <= MAX_ROUNDS:
        parser.error(f"--rounds must be between 1 and {MAX_ROUNDS}")
    if not 1 <= args.timeout <= MAX_TIMEOUT:
        parser.error(f"--timeout must be between 1 and {MAX_TIMEOUT} seconds")
    if not 0 <= args.warmup_rounds <= MAX_WARMUP_ROUNDS:
        parser.error(f"--warmup-rounds must be between 0 and {MAX_WARMUP_ROUNDS}")
    try:
        report = run(args)
    except (OSError, RuntimeError) as error:
        censored = censored_failure_report(error, args) if isinstance(error, RuntimeError) else None
        if censored is not None:
            rendered = json.dumps(censored, indent=2, sort_keys=True) + "\n"
            if args.output:
                args.output.write_text(rendered, encoding="utf-8")
            else:
                sys.stdout.write(rendered)
            return 1
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
