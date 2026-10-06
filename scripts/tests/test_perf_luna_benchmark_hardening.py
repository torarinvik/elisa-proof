"""Focused security and semantic-preflight tests for paired benchmark inputs."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_perf_luna_benchmark as baseline

from perf_build_provenance import (
    require_clean_toolchain,
    source_tree_identity,
    verify_build_artifacts,
    verify_proof_source,
)


benchmark = baseline.benchmark
manifest = baseline.manifest


class SourceAndArtifactIdentityTests(unittest.TestCase):
    def test_exact_dirty_proof_source_is_allowed_but_replacement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "src"
            root.mkdir()
            source = root / "proof.elisa"
            source.write_text("proof\n", encoding="utf-8")
            digest = source_tree_identity(root)
            pair = {"proof": manifest(), "replay": manifest()}
            for product in pair.values():
                product["proof"]["source_tree_sha256"] = digest
                product["proof"]["source_dirty"] = True
            self.assertEqual(verify_proof_source(pair, root, digest, "candidate"), digest)
            source.write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                verify_proof_source(pair, root, digest, "candidate")

    def test_source_digest_must_be_exact_and_manifest_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "src"
            root.mkdir()
            (root / "proof.elisa").write_text("proof\n", encoding="utf-8")
            digest = source_tree_identity(root)
            pair = {"proof": manifest(), "replay": manifest()}
            with self.assertRaisesRegex(RuntimeError, "manifest does not identify"):
                verify_proof_source(pair, root, digest, "baseline")
            with self.assertRaisesRegex(RuntimeError, "exact lowercase SHA-256"):
                verify_proof_source(pair, root, "not-a-digest", "baseline")

    def test_dirty_or_unknown_compiler_source_is_refused(self) -> None:
        require_clean_toolchain({"proof": manifest(), "replay": manifest()}, "clean")
        for dirty in (True, None):
            pair = {"proof": manifest(), "replay": manifest()}
            pair["proof"]["compiler"]["source_dirty"] = dirty
            with self.assertRaisesRegex(RuntimeError, "dirty or cleanliness is unknown"):
                require_clean_toolchain(pair, "unqualified")

    def test_linked_artifacts_are_rehashed_not_just_read_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = {}
            for name in ("driver", "product", "runtime", "hooks"):
                path = root / name
                path.write_bytes(name.encode())
                artifacts[name] = {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            payload = {
                "compiler": {"stage": "stage1", "executable": artifacts["driver"],
                             "product": artifacts["product"]},
                "runtime": artifacts["runtime"],
                "profile_hooks": artifacts["hooks"],
            }
            verify_build_artifacts(payload, "candidate")
            (root / "runtime").write_bytes(b"replaced")
            with self.assertRaisesRegex(RuntimeError, "runtime no longer matches"):
                verify_build_artifacts(payload, "candidate")


class SemanticPreflightTests(unittest.TestCase):
    def test_proof_inventory_trust_and_replay_match_before_timing(self) -> None:
        report = {
            "status": "proved", "verification_state": "complete",
            "summary": {"declarations": 1, "obligations": 1, "proven": 1,
                        "unproven": 0},
            "declaration_details": [{"name": "f", "verified": True}],
            "functions": [],
            "goals": [{"goal_id": 1, "name": "f", "proven": True,
                       "replay_status": "replayed"}],
            "findings": [], "certificates": [{"name": "f", "rule": "reflexivity"}],
            "replay": {"certificates": 1, "replayed": 1, "gaps": 0},
            "trust": {"trusted_assumptions": []},
        }
        package = {"format": "elisa-proof-package-v1",
                   "source": {"admissible": True, "authenticated": False},
                   "theorems": [{"statement": "true"}]}
        replay_data = {
            "format": "elisa-proof-replay-result-v1", "status": "replayed",
            "summary": {"theorems": 1, "not_replayed": 0},
            "trust": {"kernel": "checked", "source_authenticated": False},
        }
        binaries = {
            "baseline": (Path("baseline-proof"), Path("baseline-replay")),
            "candidate": (Path("candidate-proof"), Path("candidate-replay")),
        }
        calls: list[tuple[str, str]] = []
        trust_mismatch = False

        def fake_invoke(binary, arguments, timeout, side, fixture, phase):
            nonlocal trust_mismatch
            calls.append((side, phase))
            if "--json" in arguments:
                output = json.loads(json.dumps(report))
                if trust_mismatch and side == "candidate":
                    output["trust"] = {"trusted_assumptions": ["unreviewed axiom"]}
            elif "--package" in arguments:
                output = package
            else:
                output = replay_data
            return {"returncode": 0, "stdout": json.dumps(output).encode(), "stderr": b""}

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.elisa"
            source.write_text("fixture", encoding="utf-8")
            with mock.patch.object(benchmark, "invoke_for_side", side_effect=fake_invoke):
                result = benchmark.preflight_semantics(
                    binaries, (("accept", source, 0, "proved"),), 5)
            self.assertEqual(result["accept"], "matched-before-timing")
            self.assertEqual(len(calls), 6)
            self.assertTrue(all(phase.startswith("preflight-") for _, phase in calls))

            calls.clear()
            trust_mismatch = True
            with mock.patch.object(benchmark, "invoke_for_side", side_effect=fake_invoke):
                with self.assertRaisesRegex(RuntimeError, "trust roots"):
                    benchmark.preflight_semantics(
                        binaries, (("accept", source, 0, "proved"),), 5)

    def test_measurement_fields_are_excluded_but_trust_and_goals_are_not(self) -> None:
        report = {
            "status": "proved", "verification_state": "complete",
            "summary": {"obligations": 1}, "declaration_details": [],
            "functions": [], "goals": [{"goal_id": 3, "proven": True}],
            "findings": [], "certificates": [], "replay": {"gaps": 0},
            "trust": {"trusted_assumptions": []}, "measurements": {"steps": 1},
        }
        original = benchmark.semantic_projection(report)
        report["measurements"] = {"steps": 1000}
        self.assertEqual(benchmark.semantic_projection(report), original)
        self.assertEqual(benchmark.output_projection(
            "proof", json.dumps(report).encode()), benchmark.canonical_json(original))
        report["trust"] = {"trusted_assumptions": ["new"]}
        self.assertNotEqual(benchmark.semantic_projection(report), original)
        report["trust"] = original["trust"]
        report["goals"] = [{"goal_id": 4, "proven": True}]
        self.assertNotEqual(benchmark.semantic_projection(report), original)

    def test_timeout_is_structured_as_censored_not_a_speedup(self) -> None:
        error = RuntimeError(
            "candidate/resource-heavy/proof: classification=timeout; censored=true; "
            "speedup=not-reported"
        )
        result = benchmark.censored_failure_report(error)
        self.assertEqual(result["status"], "censored")
        self.assertFalse(result["timing_valid"])
        self.assertEqual(result["speedup"], "not-reported")
        self.assertTrue(result["censored_failures"][0]["censored"])
        self.assertIsNone(benchmark.censored_failure_report(RuntimeError("mismatch")))


if __name__ == "__main__":
    unittest.main()
