"""Semantic workload membership and source-pinning tests for the paired corpus."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_perf_luna_benchmark as benchmark_tests


class SemanticCorpusManifestTests(unittest.TestCase):
    def test_corpus_manifest_binds_fixture_bytes_and_harness_metadata(self) -> None:
        benchmark_tests.validate_semantic_corpus_manifest(
            benchmark_tests.SEMANTIC_CORPUS_MANIFEST
        )

    def test_workload_identity_and_expectation_mutations_are_detected(self) -> None:
        entries = benchmark_tests.SEMANTIC_CORPUS_MANIFEST
        for field, replacement in (
            ("name", "renamed-workload"), ("path", "examples/other-workload.elisa"),
            ("sha256", "0" * 64), ("expected_exit", 7), ("expected_status", "unknown"),
            ("must_prove", ("unexpected_claim",)),
            ("must_unproven", ("unexpected_open_goal",)),
            ("must_find", ("unexpected_finding",)), ("inadmissible", True),
            ("must_decline_certificates", ("unexpected_certificate",)),
        ):
            with self.subTest(field=field):
                changed = [dict(item) for item in entries]
                changed[0][field] = replacement
                with self.assertRaisesRegex(AssertionError, "manifest"):
                    benchmark_tests.validate_semantic_corpus_manifest(changed)

    def test_source_byte_change_is_rejected_even_with_original_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entries = benchmark_tests.SEMANTIC_CORPUS_MANIFEST
            for item in entries:
                destination = root / item["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((benchmark_tests.ROOT / item["path"]).read_bytes())
            target = root / entries[0]["path"]
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "bytes/hash changed"):
                benchmark_tests.validate_semantic_corpus_manifest(entries, root=root)

    def test_replay_contract_mutation_is_detected(self) -> None:
        requirements = benchmark_tests.CORPUS_REPLAY_REQUIREMENTS
        entries = benchmark_tests.SEMANTIC_CORPUS_MANIFEST
        with mock.patch.dict(requirements, {"zero_replay_gaps": False}):
            with self.assertRaisesRegex(AssertionError, "replay requirements"):
                benchmark_tests.validate_semantic_corpus_manifest(entries)
        with mock.patch.object(benchmark_tests, "CORPUS_REPORT_FIELDS", ("status",)):
            with self.assertRaisesRegex(AssertionError, "report fields"):
                benchmark_tests.validate_semantic_corpus_manifest(entries)


if __name__ == "__main__":
    unittest.main()
