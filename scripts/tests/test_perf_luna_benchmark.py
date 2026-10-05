#!/usr/bin/env python3
"""Focused stdlib tests for benchmark provenance and sampling behavior."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import argparse
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from perf_build_provenance import (  # noqa: E402
    read_build_manifest,
    require_compatible_products,
    shared_product_context,
)


SPEC = importlib.util.spec_from_file_location(
    "perf_luna_benchmark_under_test", SCRIPTS / "perf_luna_benchmark.py"
)
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def manifest(stage: str = "stage1", runtime: str | None = "runtime") -> dict:
    return {
        "proof": {"source_tree_sha256": "source"},
        "frontend": {"revision": "front-rev", "tree": "front-tree"},
        "compiler": {
            "stage": stage,
            "product": {"sha256": "compiler-product"},
            "executable": {"sha256": "compiler-executable"},
        },
        "runtime": {"sha256": runtime},
        "profile_hooks": {"sha256": "hooks"},
        "target": "arm64-test",
        "optimization": "O2",
        "compile_mode": "strict",
        "compiler_flags": ["-O2", "-strict"],
    }


def write_manifest(binary: Path, payload: object, *, checksum: bool = True) -> None:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    path = Path(str(binary) + ".manifest.json")
    path.write_bytes(raw)
    sidecar = Path(str(path) + ".sha256")
    sidecar.write_text(hashlib.sha256(raw).hexdigest() if checksum else "0" * 64,
                       encoding="ascii")


# Test-owned semantic corpus lock. Keeping the source digest and the expected
# workload contract here makes fixture drift explicit and reviewable; these are
# identity/coverage checks, not measured performance results.
CORPUS_REPORT_FIELDS = (
    "status", "summary.declarations", "summary.obligations",
    "summary.proven", "summary.unproven", "declaration_details", "goals",
    "certificates", "replay.certificates", "replay.replayed", "replay.gaps",
)
SEMANTIC_CORPUS_MANIFEST = (
    {
        "name": "accept", "path": "examples/perf_luna_accept.elisa",
        "sha256": "b98bc4c879e7ca4279515ade0c248d125f9323a1f3e01f9bed389fc9a818354b",
        "expected_exit": 0, "expected_status": "proved",
        "must_prove": (), "must_unproven": (), "must_find": (), "inadmissible": False,
        "must_decline_certificates": (),
    },
    {
        "name": "refusal", "path": "examples/perf_luna_refusal.elisa",
        "sha256": "5bb1c84d7baf95c9853e448062184a3427b298d80b205ed7cd9ac8032a7cd454",
        "expected_exit": 1, "expected_status": "failed",
        "must_prove": (), "must_unproven": ("perf_luna_must_remain_open",),
        "must_find": (), "inadmissible": False,
        "must_decline_certificates": (),
    },
    {
        "name": "symbolic_quantifier", "path": "examples/symbolic_quantifier.elisa",
        "sha256": "eb8ea811bdf07e0796eeecc929a0b007bb44813724214e8bbc952a65325e0e9e",
        "expected_exit": 0, "expected_status": "proved",
        "must_prove": (), "must_unproven": (), "must_find": (), "inadmissible": False,
        "must_decline_certificates": (),
    },
    {
        "name": "rejected_symbolic_quantifier",
        "path": "examples/rejected_symbolic_quantifier.elisa",
        "sha256": "5c1990bafd783178ad4bc66916fa35c16b8670a7dc30d8443f077b161cd3b352",
        "expected_exit": 1, "expected_status": "failed",
        "must_prove": (),
        "must_unproven": (
            "bubble_pass_strict", "congruence_other_index", "congruence_other_container",
            "negated_not_strict", "negated_wrong_direction", "guard_not_refuted",
            "guard_mentions_binder", "guard_not_negated", "instance_outside",
            "lower_missing_point", "lower_two_short", "narrow_keeps_write",
            "binding_other_value", "subscript_unequal", "subscript_other_container",
            "alias_outside", "alias_other_container", "alias_carried_outside",
        ),
        "must_find": (), "inadmissible": True,
        "must_decline_certificates": (
            "off_by_one", "wrong_lower", "other_body", "shadow", "weaken_wrong_way",
            "weaken_wider", "weaken_grown_missing_point", "element_not_strict",
        ),
    },
    {
        "name": "congruence", "path": "examples/congruence.elisa",
        "sha256": "99b0a7a7712de6c427ed84eedfb4853e5639c83fb35c224a6d14c9c08bdaebca",
        "expected_exit": 0, "expected_status": "proved",
        "must_prove": (), "must_unproven": (), "must_find": (), "inadmissible": False,
        "must_decline_certificates": (),
    },
    {
        "name": "rejected_congruence", "path": "examples/rejected_congruence.elisa",
        "sha256": "8cd9f33f34c9fa124aa9bad5740a3619000a71dcab706274f9d1c7f9f1e6e534",
        "expected_exit": 1, "expected_status": "failed",
        "must_prove": ("indexed_element", "call_congruence"),
        "must_unproven": (),
        "must_find": (
            "disequality_premise", "order_premise", "disjunctive_premise",
            "unrelated_operand", "distinct_former", "struct_equality_premise",
            "local_struct_equality_premise", "constructed_aggregate", "cross_width",
            "wrapping_operand",
        ),
        "inadmissible": False,
        "must_decline_certificates": (),
    },
)
CORPUS_REPLAY_REQUIREMENTS = {
    "proof_report_fields": CORPUS_REPORT_FIELDS,
    "zero_replay_gaps": True,
    "certificate_count_equals_replayed": True,
    "claimed_goal_requires_replay_status": "replayed",
}
EXPECTED_CORPUS_REPLAY_REQUIREMENTS = {
    "proof_report_fields": (
        "status", "summary.declarations", "summary.obligations",
        "summary.proven", "summary.unproven", "declaration_details", "goals",
        "certificates", "replay.certificates", "replay.replayed", "replay.gaps",
    ),
    "zero_replay_gaps": True,
    "certificate_count_equals_replayed": True,
    "claimed_goal_requires_replay_status": "replayed",
}


def validate_semantic_corpus_manifest(entries, *, root: Path = ROOT) -> None:
    """Fail closed on changed workload identity or semantic/replay contract."""
    if tuple(entries) != SEMANTIC_CORPUS_MANIFEST:
        raise AssertionError("semantic benchmark corpus manifest differs from its reviewed contract")
    fixture_projection = tuple(
        (item["name"], ROOT / item["path"], item["expected_exit"], item["expected_status"])
        for item in entries
    )
    if fixture_projection != benchmark.FIXTURES:
        raise AssertionError("semantic corpus manifest no longer matches benchmark fixtures")
    for item in entries:
        source = root / item["path"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise AssertionError(f"semantic workload bytes/hash changed: {item['name']}")
    for name, expected in (
        ("must_prove", benchmark.MUST_PROVE),
        ("must_unproven", benchmark.MUST_REMAIN_UNPROVEN),
        ("must_find", benchmark.MUST_HAVE_FINDINGS),
    ):
        actual = {item["name"]: item[name] for item in entries if item[name]}
        if actual != expected:
            raise AssertionError(f"semantic corpus {name} metadata differs from benchmark harness")
    expected_inadmissible = {item["name"] for item in entries if item["inadmissible"]}
    if expected_inadmissible != benchmark.MUST_BE_INADMISSIBLE:
        raise AssertionError("semantic corpus admissibility metadata differs from benchmark harness")
    expected_declines = {
        item["name"]: item["must_decline_certificates"]
        for item in entries if item["must_decline_certificates"]
    }
    if expected_declines != benchmark.MUST_DECLINE_QUANTIFIER_CERTIFICATE:
        raise AssertionError("semantic corpus declined-certificate metadata differs from benchmark harness")
    if CORPUS_REPORT_FIELDS != EXPECTED_CORPUS_REPLAY_REQUIREMENTS["proof_report_fields"]:
        raise AssertionError("semantic corpus required report fields changed")
    if CORPUS_REPLAY_REQUIREMENTS != EXPECTED_CORPUS_REPLAY_REQUIREMENTS:
        raise AssertionError("semantic corpus replay requirements changed")


class SemanticCorpusManifestTests(unittest.TestCase):
    def test_corpus_manifest_binds_fixture_bytes_and_harness_metadata(self) -> None:
        validate_semantic_corpus_manifest(SEMANTIC_CORPUS_MANIFEST)

    def test_workload_identity_and_expectation_mutations_are_detected(self) -> None:
        for field, replacement in (
                ("name", "renamed-workload"),
                ("path", "examples/other-workload.elisa"),
                ("sha256", "0" * 64),
                ("expected_exit", 7),
                ("expected_status", "unknown"),
                ("must_prove", ("unexpected_claim",)),
                ("must_unproven", ("unexpected_open_goal",)),
                ("must_find", ("unexpected_finding",)),
                ("inadmissible", True),
                ("must_decline_certificates", ("unexpected_certificate",))):
            with self.subTest(field=field):
                changed = [dict(item) for item in SEMANTIC_CORPUS_MANIFEST]
                changed[0][field] = replacement
                with self.assertRaisesRegex(AssertionError, "manifest"):
                    validate_semantic_corpus_manifest(changed)

    def test_source_byte_change_is_rejected_even_with_original_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for item in SEMANTIC_CORPUS_MANIFEST:
                destination = root / item["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / item["path"]).read_bytes())
            target = root / SEMANTIC_CORPUS_MANIFEST[0]["path"]
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "bytes/hash changed"):
                validate_semantic_corpus_manifest(SEMANTIC_CORPUS_MANIFEST, root=root)

    def test_replay_contract_mutation_is_detected(self) -> None:
        with mock.patch.dict(CORPUS_REPLAY_REQUIREMENTS, {"zero_replay_gaps": False}):
            with self.assertRaisesRegex(AssertionError, "replay requirements"):
                validate_semantic_corpus_manifest(SEMANTIC_CORPUS_MANIFEST)
        with mock.patch(__name__ + ".CORPUS_REPORT_FIELDS", ("status",)):
            with self.assertRaisesRegex(AssertionError, "report fields"):
                validate_semantic_corpus_manifest(SEMANTIC_CORPUS_MANIFEST)


class ManifestReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.binary = Path(self.temp.name) / "proof"
        self.binary.write_bytes(b"test executable bytes")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_manifest_is_read(self) -> None:
        digest = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        payload = {"binary": {"sha256": digest}}
        write_manifest(self.binary, payload)
        self.assertEqual(read_build_manifest(self.binary, "proof"), payload)

    def test_absent_manifest_and_sidecar_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "missing or invalid"):
            read_build_manifest(self.binary, "proof")
        write_manifest(self.binary, {"binary": {"sha256": "unused"}})
        Path(str(self.binary) + ".manifest.json.sha256").unlink()
        with self.assertRaisesRegex(RuntimeError, "missing or invalid"):
            read_build_manifest(self.binary, "proof")

    def test_malformed_json_and_non_object_manifest_are_rejected(self) -> None:
        path = Path(str(self.binary) + ".manifest.json")
        sidecar = Path(str(path) + ".sha256")
        path.write_bytes(b"{")
        sidecar.write_text(hashlib.sha256(b"{").hexdigest(), encoding="ascii")
        with self.assertRaisesRegex(RuntimeError, "missing or invalid"):
            read_build_manifest(self.binary, "proof")
        write_manifest(self.binary, ["not", "an", "object"])
        with self.assertRaisesRegex(RuntimeError, "not a JSON object"):
            read_build_manifest(self.binary, "proof")

    def test_bad_checksum_and_binary_digest_mismatch_are_rejected(self) -> None:
        write_manifest(self.binary, {"binary": {"sha256": "unused"}}, checksum=False)
        with self.assertRaisesRegex(RuntimeError, "checksum"):
            read_build_manifest(self.binary, "proof")
        write_manifest(self.binary, {"binary": {"sha256": "not-the-binary"}})
        with self.assertRaisesRegex(RuntimeError, "does not identify"):
            read_build_manifest(self.binary, "proof")

    def test_missing_binary_identity_is_rejected(self) -> None:
        write_manifest(self.binary, {})
        with self.assertRaisesRegex(RuntimeError, "does not identify"):
            read_build_manifest(self.binary, "proof")


class ProductIdentityTests(unittest.TestCase):
    def test_proof_replay_frontend_or_source_mismatch_is_rejected(self) -> None:
        proof = manifest()
        replay = manifest()
        replay["frontend"]["revision"] = "different"
        with self.assertRaisesRegex(RuntimeError, "frontend.revision"):
            require_compatible_products(proof, replay, "pair")

        replay = manifest()
        replay["proof"]["source_tree_sha256"] = "different-source"
        with self.assertRaisesRegex(RuntimeError, "proof.source_tree_sha256"):
            require_compatible_products(proof, replay, "pair")

    def test_required_identity_fields_cannot_be_absent(self) -> None:
        malformed = manifest()
        malformed["compiler"]["product"].pop("sha256")
        with self.assertRaisesRegex(RuntimeError, "compiler.product.sha256"):
            require_compatible_products(manifest(), malformed, "pair")

    def test_stage0_may_omit_runtime_but_stage1_may_not(self) -> None:
        stage0 = manifest(stage="stage0", runtime=None)
        context = require_compatible_products(stage0, manifest(stage="stage0", runtime=None), "stage0")
        self.assertIsNone(context["runtime.sha256"])

        with self.assertRaisesRegex(RuntimeError, "runtime.sha256"):
            require_compatible_products(manifest(runtime=None), manifest(runtime=None), "stage1")

        # Optional means absent on both sides, not permission to pair different runtimes.
        with self.assertRaisesRegex(RuntimeError, "runtime.sha256"):
            require_compatible_products(stage0, manifest(stage="stage0", runtime="other"), "stage0")

    def test_shared_context_compares_stage_and_all_toolchain_keys(self) -> None:
        base = manifest()
        context = shared_product_context(base)
        for key, update in (
            ("compiler stage", lambda m: m["compiler"].update(stage="stage0")),
            ("compiler product", lambda m: m["compiler"]["product"].update(sha256="other")),
            ("runtime", lambda m: m["runtime"].update(sha256="other")),
            ("optimization", lambda m: m.update(optimization="O0")),
            ("compiler flags", lambda m: m.update(compiler_flags=["-O0"])),
        ):
            with self.subTest(key=key):
                changed = manifest()
                update(changed)
                with self.assertRaises(RuntimeError):
                    require_compatible_products(base, changed, "pair")
        self.assertEqual(context["compiler.stage"], "stage1")

    def test_baseline_and_candidate_toolchains_must_match_but_source_may_differ(self) -> None:
        baseline = require_compatible_products(manifest(), manifest(), "baseline")
        candidate_manifest = manifest()
        candidate_manifest["proof"]["source_tree_sha256"] = "candidate-source"
        candidate = require_compatible_products(candidate_manifest, candidate_manifest, "candidate")
        toolchain_keys = tuple(key for key in baseline if not key.startswith("proof."))
        self.assertEqual({key: baseline[key] for key in toolchain_keys},
                         {key: candidate[key] for key in toolchain_keys})
        self.assertNotEqual(baseline["proof.source_tree_sha256"],
                            candidate["proof.source_tree_sha256"])

        candidate_manifest["frontend"]["tree"] = "different-tree"
        candidate = require_compatible_products(candidate_manifest, candidate_manifest, "candidate")
        differences = [key for key in toolchain_keys if baseline[key] != candidate[key]]
        self.assertEqual(differences, ["frontend.tree"])

    def test_run_preflight_rejects_baseline_candidate_toolchain_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                "baseline_proof": root / "baseline-proof",
                "baseline_replay": root / "baseline-replay",
                "candidate_proof": root / "candidate-proof",
                "candidate_replay": root / "candidate-replay",
            }
            for binary in paths.values():
                binary.write_bytes(b"executable")
                binary.chmod(0o755)
            baseline = manifest()
            candidate = manifest()
            candidate["frontend"]["revision"] = "different-compiler-front"
            args = argparse.Namespace(
                baseline_proof=paths["baseline_proof"],
                baseline_replay=paths["baseline_replay"],
                candidate_proof=paths["candidate_proof"],
                candidate_replay=paths["candidate_replay"],
            )
            with mock.patch.object(
                benchmark, "read_build_manifest",
                side_effect=[baseline, baseline, candidate, candidate],
            ):
                with self.assertRaisesRegex(RuntimeError, "different frontends or toolchains"):
                    benchmark.run(args)

    def test_manifest_is_revalidated_after_file_identity_snapshot(self) -> None:
        binaries = {
            "baseline": (Path("baseline-proof"), Path("baseline-replay")),
            "candidate": (Path("candidate-proof"), Path("candidate-replay")),
        }
        original = manifest()
        changed = manifest()
        changed["binary"] = {"sha256": "changed-binary"}
        manifests = {
            label: {role: original for role in ("proof", "replay")}
            for label in binaries
        }
        with mock.patch.object(benchmark, "read_build_manifest", return_value=changed):
            with mock.patch.object(benchmark, "require_unchanged_inputs"):
                with self.assertRaisesRegex(RuntimeError, "changed while creating benchmark snapshot"):
                    benchmark.verify_build_snapshot(binaries, manifests, {})


class SamplingTests(unittest.TestCase):
    @staticmethod
    def sample(seconds: float) -> dict:
        return {"wall_seconds": seconds, "user_cpu_seconds": seconds / 2,
                "system_cpu_seconds": seconds / 4, "peak_rss_kib": int(seconds * 100)}

    def test_p95_uses_nearest_rank_not_interpolation(self) -> None:
        summary = benchmark.record_measurements([self.sample(n) for n in range(1, 21)])
        self.assertEqual(summary["p95_wall_seconds"], 19.0)

    def test_single_sample_p95_is_that_sample(self) -> None:
        summary = benchmark.record_measurements([self.sample(3.25)])
        self.assertEqual(summary["p95_wall_seconds"], 3.25)

    @staticmethod
    def semantic_report(status: str = "proved", *, obligations: int = 1,
                        proven: int = 1, unproven: int = 0) -> tuple[dict, dict]:
        goals = [{"name": "claim", "proven": proven == 1}] if obligations else []
        certificates = [{"name": "claim", "rule": "reflexivity"}] if proven else []
        report = {
            "status": status,
            "summary": {"declarations": 1, "obligations": obligations,
                        "proven": proven, "unproven": unproven},
            "declaration_details": [{"name": "claim", "verified": proven == 1}],
            "goals": goals,
            "certificates": certificates,
            "replay": {"certificates": len(certificates), "replayed": len(certificates), "gaps": 0},
        }
        return {"stdout": json.dumps(report, separators=(",", ":")).encode()}, report

    def test_semantic_workload_metrics_for_proved_report(self) -> None:
        result, report = self.semantic_report()
        metrics = benchmark.semantic_workload_metrics(result, report, "positive")
        self.assertEqual(metrics["classification"], "proved")
        self.assertEqual(metrics["declarations"], 1)
        self.assertEqual(metrics["verified_declarations"], 1)
        self.assertEqual(metrics["obligations"], 1)
        self.assertEqual(metrics["proof_bytes"], len(result["stdout"]))
        self.assertEqual(metrics["certificate_count"], 1)
        self.assertGreater(metrics["certificate_bytes_compact_json"], 0)
        self.assertEqual(metrics["replayed_count"], 1)
        self.assertEqual(metrics["replay_gaps"], 0)
        self.assertTrue(metrics["complete"])

    def test_semantic_workload_metrics_classify_expected_refusal(self) -> None:
        result, report = self.semantic_report("failed", proven=0, unproven=1)
        report["goals"][0]["proven"] = False
        metrics = benchmark.semantic_workload_metrics(result, report, "refusal")
        self.assertEqual(metrics["classification"], "refusal")
        self.assertEqual(metrics["obligations"], 1)
        self.assertEqual(metrics["certificate_count"], 0)
        self.assertEqual(metrics["replayed_count"], 0)

    def test_incomplete_report_is_censored_not_measurable(self) -> None:
        result, report = self.semantic_report()
        report["summary"]["obligations"] = 2
        with self.assertRaisesRegex(RuntimeError, "incomplete semantic workload report"):
            benchmark.semantic_workload_metrics(result, report, "incomplete")

        report["summary"]["obligations"] = 1
        report["replay"]["gaps"] = 1
        with self.assertRaisesRegex(RuntimeError, "incomplete semantic workload report"):
            benchmark.semantic_workload_metrics(result, report, "replay-gap")

    def test_timeout_names_censored_side_and_suppresses_speedup(self) -> None:
        with mock.patch.object(benchmark, "invoke", side_effect=RuntimeError("measurement wrapper timed out")):
            with self.assertRaisesRegex(
                    RuntimeError,
                    r"candidate/fixture/proof: classification=timeout; censored=true; speedup=not-reported"):
                benchmark.invoke_for_side(Path("candidate-proof"), ["--json", "fixture"],
                                           1, "candidate", "fixture", "proof")

    def test_warmups_are_excluded_and_variant_order_alternates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "tiny.elisa"
            source.write_text("fixture", encoding="utf-8")
            binaries = {
                "baseline": (root / "baseline-proof", root / "baseline-replay"),
                "candidate": (root / "candidate-proof", root / "candidate-replay"),
            }
            for pair in binaries.values():
                for binary in pair:
                    binary.write_bytes(binary.name.encode())
                    binary.chmod(0o755)
                    write_manifest(binary, {"binary": {"sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}})
                    Path(str(binary) + ".manifest.json.sha256").write_text("fixture", encoding="ascii")
            context = manifest()
            proof_bytes = json.dumps({
                "status": "proved", "goals": [], "findings": [], "functions": [],
                "summary": {"declarations": 0, "obligations": 0, "proven": 0, "unproven": 0},
                "declaration_details": [], "certificates": [],
                "replay": {"gaps": 0, "certificates": 0, "replayed": 0},
            }).encode()
            package_bytes = json.dumps({
                "format": "elisa-proof-package-v1",
                "source": {"admissible": True, "authenticated": False},
                "theorems": [],
            }).encode()
            replay_bytes = json.dumps({
                "format": "elisa-proof-replay-result-v1", "status": "rejected",
                "reason": "no-theorems",
                "trust": {"kernel": "checked", "source_authenticated": False},
            }).encode()
            calls: list[tuple[str, str, str]] = []

            def fake_invoke(binary: Path, arguments: list[str], timeout: int) -> dict:
                variant = "baseline" if Path(binary).name.startswith("baseline-") else "candidate"
                if "--json" in arguments:
                    phase, output, exit_code = "proof", proof_bytes, 0
                elif "--package" in arguments:
                    phase, output, exit_code = "export", package_bytes, 0
                else:
                    phase, output, exit_code = "replay", replay_bytes, 1
                calls.append((variant, phase, Path(arguments[-1]).name))
                return {"returncode": exit_code, "stdout": output, "stderr": b"",
                        "wall_seconds": 1000.0 if len(calls) <= 6 else 1.0,
                        "user_cpu_seconds": 0.1, "system_cpu_seconds": 0.1,
                        "peak_rss_kib": 100}

            args = argparse.Namespace(
                baseline_proof=binaries["baseline"][0],
                baseline_replay=binaries["baseline"][1],
                candidate_proof=binaries["candidate"][0],
                candidate_replay=binaries["candidate"][1],
                rounds=2, warmup_rounds=1, timeout=1,
            )
            with mock.patch.object(benchmark, "FIXTURES", (("tiny", source, 0, "proved"),)), \
                    mock.patch.object(benchmark, "read_build_manifest", return_value=context), \
                    mock.patch.object(benchmark, "require_compatible_products", return_value=context), \
                    mock.patch.object(benchmark, "invoke", side_effect=fake_invoke), \
                    mock.patch.object(benchmark, "file_identity", side_effect=lambda path: {"sha256": "fixture", "size_bytes": Path(path).stat().st_size}), \
                    mock.patch.object(benchmark, "require_unchanged_inputs"):
                result = benchmark.run(args)

            self.assertEqual([(variant, phase) for variant, phase, _ in calls], [
                ("baseline", "proof"), ("baseline", "export"), ("baseline", "replay"),
                ("candidate", "proof"), ("candidate", "export"), ("candidate", "replay"),
                ("candidate", "proof"), ("candidate", "export"), ("candidate", "replay"),
                ("baseline", "proof"), ("baseline", "export"), ("baseline", "replay"),
                ("baseline", "proof"), ("baseline", "export"), ("baseline", "replay"),
                ("candidate", "proof"), ("candidate", "export"), ("candidate", "replay"),
            ])
            fixture = result["fixtures"][0]
            self.assertEqual(fixture["semantic_workload"]["baseline"]["classification"], "proved")
            self.assertEqual(fixture["semantic_workload"]["candidate"]["classification"], "proved")
            self.assertEqual(fixture["semantic_workload"]["baseline"],
                             fixture["semantic_workload"]["candidate"])
            for phase_key in ("proof", "package_export", "standalone_replay"):
                for variant in ("baseline", "candidate"):
                    self.assertEqual(fixture[phase_key][variant]["rounds"], 2)
                    self.assertEqual(fixture[phase_key][variant]["median_wall_seconds"], 1.0)
            self.assertEqual(result["rounds"], 2)
            self.assertEqual(result["warmup_rounds"], 1)


if __name__ == "__main__":
    unittest.main()
