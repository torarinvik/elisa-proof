"""Offline validation tests for durable paired benchmark reports."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from perf_luna_evidence_validation import validate_report  # noqa: E402


DIGEST = "a" * 64


def make_report() -> dict:
    context = {
        "proof.source_tree_sha256": DIGEST, "frontend.revision": "b" * 40,
        "frontend.tree": "c" * 40, "compiler.stage": "stage1",
        "compiler.stage1_revision": "d" * 8, "compiler.source_revision": "compiler-src",
        "compiler.source_dirty": False, "compiler.product.sha256": DIGEST,
        "compiler.executable.sha256": DIGEST, "runtime.sha256": DIGEST,
        "profile_hooks.sha256": None, "target": "arm64-test", "optimization": "O2",
        "compile_mode": "strict", "compiler_flags": ["-O2"],
    }
    identity = {"sha256": DIGEST, "size_bytes": 10}
    measurement = {
        "rounds": 3, "p50_wall_seconds": 1.0, "p95_wall_seconds": 1.2,
        "minimum_wall_seconds": 0.9, "maximum_wall_seconds": 1.2,
        "wall_spread_seconds": 0.3, "p50_user_cpu_seconds": 0.5,
        "p50_system_cpu_seconds": 0.1, "peak_rss_kib": 1024,
    }
    fixture = {
        "fixture": "symbolic_quantifier", "source": identity,
        "expected_status": "proved", "expected_exit": 0,
        "proof": {"baseline": measurement, "candidate": measurement},
        "package_export": {"baseline": measurement, "candidate": measurement},
        "standalone_replay": {"baseline": measurement, "candidate": measurement},
        "semantic_workload": {"baseline": {"complete": True, "replay_gaps": 0,
            "certificate_count": 4, "replayed_count": 4, "obligations": 4},
            "candidate": {"complete": True, "replay_gaps": 0,
            "certificate_count": 4, "replayed_count": 4, "obligations": 4}},
        "semantic_outcomes": {arm: {
            "proof_status": "proved", "proof_summary": {"obligations": 4},
            "obligation_count": 4, "obligation_inventory_sha256": DIGEST,
            "proof_trust": {"trusted_assumptions": [], "trusted_boundary_facts": 0,
                "kernel_replayed_certificates": 4, "full_projection_sha256": DIGEST},
            "proof_replay": {"certificates": 4, "replayed": 4, "gaps": 0},
            "package_admissible": True, "package_theorem_count": 4,
            "package_theorem_inventory_sha256": DIGEST,
            "standalone_replay_status": "replayed",
            "standalone_replay_summary": {"theorems": 4, "not_replayed": 0},
            "standalone_replay_trust": {"kernel": "checked"},
        } for arm in ("baseline", "candidate")},
        "semantic_output_sha256": {arm: {phase: DIGEST for phase in ("proof", "export", "replay")}
                                   for arm in ("baseline", "candidate")},
        "paired_samples": {phase: {arm: [
            {"pair_index": index, "wall_seconds": 1.0, "user_cpu_seconds": 0.5,
             "system_cpu_seconds": 0.1, "peak_rss_kib": 1024}
            for index in range(1, 4)] for arm in ("baseline", "candidate")}
            for phase in ("proof", "export", "replay")},
        "semantic_outputs_identical": True,
    }
    products = {}
    build_manifests = {}
    for arm in ("baseline", "candidate"):
        products[arm] = {"proof_identity": identity, "replay_identity": identity}
        build_manifests[arm] = {}
        for role in ("proof", "replay"):
            manifest = {
                "binary": {"sha256": DIGEST}, "proof": {"source_tree_sha256": DIGEST,
                "source_dirty": False}, "frontend": {"revision": "b" * 40, "tree": "c" * 40},
                "compiler": {"stage": "stage1", "stage1_revision": "d" * 8,
                    "source_revision": "compiler-src", "source_dirty": False,
                    "product": {"sha256": DIGEST}, "executable": {"sha256": DIGEST}},
                "runtime": {"sha256": DIGEST}, "profile_hooks": {"sha256": None},
                "target": "arm64-test", "optimization": "O2", "compile_mode": "strict",
                "compiler_flags": ["-O2"],
            }
            raw = json.dumps(manifest, separators=(",", ":"))
            build_manifests[arm][role] = raw
            products[arm][role + "_manifest_identity"] = {
                "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "size_bytes": len(raw.encode()),
            }
    return {
        "schema": "elisa-proof-perf-luna-v4", "measurement_order": "alternating-baseline-candidate",
        "rounds": 3, "warmup_rounds": 1, "build_context": {"baseline": context,
            "candidate": copy.deepcopy(context)}, "source_tree_sha256": {"baseline": DIGEST, "candidate": DIGEST},
        "binaries": products, "build_manifests": build_manifests,
        "selected_fixtures": ["symbolic_quantifier"], "fixtures": [fixture],
    }


class EvidenceValidationTests(unittest.TestCase):
    def test_accepts_complete_paired_report(self) -> None:
        result = validate_report(make_report())
        self.assertTrue(result["valid"])
        self.assertEqual(result["speedup_claim"], "none-asserted")

    def test_rejects_mismatched_toolchain(self) -> None:
        report = make_report()
        report["build_context"]["candidate"]["runtime.sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "different compiler/frontend/runtime/target"):
            validate_report(report)

    def test_rejects_semantic_or_replay_mismatch(self) -> None:
        report = make_report()
        report["fixtures"][0]["semantic_output_sha256"]["candidate"]["replay"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "semantic outputs differ"):
            validate_report(report)
        report = make_report()
        report["fixtures"][0]["semantic_workload"]["candidate"]["replay_gaps"] = 1
        with self.assertRaisesRegex(ValueError, "metrics differ"):
            validate_report(report)
        report = make_report()
        report["fixtures"][0]["semantic_outcomes"]["candidate"]["proof_trust"] = {
            "trusted_assumptions": ["new-axiom"]
        }
        with self.assertRaisesRegex(ValueError, "obligation/replay/trust outcomes differ"):
            validate_report(report)

    def test_rejects_manifest_payload_replacement(self) -> None:
        report = make_report()
        report["build_manifests"]["baseline"]["proof"] = "{}"
        with self.assertRaisesRegex(ValueError, "manifest digest does not match"):
            validate_report(report)

    def test_rejects_incomplete_samples_and_untrusted_toolchain(self) -> None:
        report = make_report()
        report["fixtures"][0]["proof"]["baseline"]["rounds"] = 2
        with self.assertRaisesRegex(ValueError, "sample count is incomplete"):
            validate_report(report)
        report = make_report()
        report["build_context"]["baseline"]["compiler.source_dirty"] = True
        with self.assertRaisesRegex(ValueError, "compiler source is not clean"):
            validate_report(report)


if __name__ == "__main__":
    unittest.main()
