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
            for phase_key in ("proof", "package_export", "standalone_replay"):
                for variant in ("baseline", "candidate"):
                    self.assertEqual(fixture[phase_key][variant]["rounds"], 2)
                    self.assertEqual(fixture[phase_key][variant]["median_wall_seconds"], 1.0)
            self.assertEqual(result["rounds"], 2)
            self.assertEqual(result["warmup_rounds"], 1)


if __name__ == "__main__":
    unittest.main()
