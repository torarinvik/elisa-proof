"""Adversarial checks for the versioned, source-pinned proof workload corpus."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from perf_luna_benchmark import FIXTURES, FIXTURE_SHA256  # noqa: E402
from perf_luna_corpus import (  # noqa: E402
    CENSORED_STATES,
    CorpusError,
    REQUIRED_WORKLOADS,
    load_corpus,
    validate_all,
    validate_result,
    validate_sources,
)
import test_perf_luna_benchmark as benchmark_tests  # noqa: E402


class WorkloadManifestTests(unittest.TestCase):
    def test_reviewed_corpus_is_complete_and_matches_pinned_committed_sources(self) -> None:
        corpus = validate_all()
        names = {entry["name"] for entry in corpus["workloads"]}
        self.assertEqual(names, REQUIRED_WORKLOADS)
        self.assertEqual(len(corpus["workloads"]), 15)
        self.assertEqual(sum(item["role"] == "timed_fixture"
                             for item in corpus["workloads"]), 6)
        self.assertEqual(sum(item["role"] == "project_workload"
                             for item in corpus["workloads"]), 9)
        timed = [item for item in corpus["workloads"]
                 if item["role"] == "timed_fixture"]
        self.assertEqual(
            tuple((item["name"], ROOT / item["path"],
                   item["expected_outcome"]["exit_code"],
                   item["expected_outcome"]["proof_status"]) for item in timed),
            FIXTURES,
        )
        self.assertEqual(
            {item["name"]: item["source_files"][0]["sha256"] for item in timed},
            FIXTURE_SHA256,
        )
        self.assertIn(
            "src/proof/kernel_core.elisa",
            {source["path"] for item in corpus["workloads"]
             for source in item["source_files"]},
        )

    def test_removing_required_project_case_is_rejected(self) -> None:
        corpus = load_corpus()
        corpus["workloads"] = [item for item in corpus["workloads"]
                               if item["name"] != "dogfood_kernel_core"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            path.write_text(json.dumps(corpus), encoding="utf-8")
            with self.assertRaisesRegex(CorpusError, "required workload cases are missing"):
                load_corpus(path)

    def test_stale_manifest_hash_is_rejected_against_git_pinned_bytes(self) -> None:
        corpus = copy.deepcopy(load_corpus())
        item = next(item for item in corpus["workloads"] if item["name"] == "kernel_core")
        item["source_files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(CorpusError, "manifest hash is stale"):
            validate_sources(corpus)

    def test_source_provenance_includes_the_kernel_for_dogfood_inputs(self) -> None:
        corpus = load_corpus()
        for name in ("dogfood_kernel_core", "rejected_dogfood_kernel_core"):
            item = next(item for item in corpus["workloads"] if item["name"] == name)
            paths = {source["path"] for source in item["source_files"]}
            self.assertEqual(paths, {
                item["path"], "src/proof/kernel_core.elisa",
            })


class ResultCompletenessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entry = next(item for item in load_corpus()["workloads"]
                          if item["name"] == "dogfood_kernel_core")
        self.result = {
            "state": "complete", "stdout_truncated": False,
            "exit_code": 0, "proof_status": "proved", "replay_gaps": 0,
            "semantic_category": "proved",
            "requested_samples": 7, "completed_samples": 7,
        }

    def test_complete_replay_closed_result_is_accepted(self) -> None:
        validate_result(self.entry, self.result)

    def test_each_censored_state_is_rejected(self) -> None:
        for state in CENSORED_STATES:
            with self.subTest(state=state):
                result = dict(self.result, state=state)
                with self.assertRaisesRegex(CorpusError, "censored result state"):
                    validate_result(self.entry, result)

    def test_native_paired_benchmark_censor_record_is_rejected(self) -> None:
        result = dict(self.result)
        result.update({
            "status": "censored", "timing_valid": False,
            "censored_failures": [{"censored": True, "message": "watchdog timeout"}],
        })
        with self.assertRaisesRegex(CorpusError, "censored failures"):
            validate_result(self.entry, result)

    def test_missing_state_truncation_wrong_semantics_and_replay_gaps_are_rejected(self) -> None:
        cases = (
            ({key: value for key, value in self.result.items() if key != "state"}, "missing complete-run"),
            (dict(self.result, state=[]), "missing complete-run"),
            (dict(self.result, state="complete", stdout_truncated=True), "truncated stdout"),
            (dict(self.result, state="complete", program_stdout_truncated=True), "truncated stdout"),
            (dict(self.result, proof_status="failed"), "proof status differs"),
            (dict(self.result, semantic_category="expected_refusal"), "semantic category differs"),
            (dict(self.result, exit_code=1), "exit code differs"),
            (dict(self.result, replay_gaps=1), "not replay-closed"),
            (dict(self.result, completed_samples=6), "sample set is missing"),
            (dict(self.result, requested_samples=0, completed_samples=0), "sample set is missing"),
        )
        for result, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(CorpusError, message):
                    validate_result(self.entry, result)

    def test_budget_timeout_is_a_semantic_refusal_not_a_censored_run(self) -> None:
        entry = next(item for item in load_corpus()["workloads"]
                     if item["name"] == "bounded_model_work_budget")
        result = {
            "state": "complete", "stdout_truncated": False,
            "exit_code": 1, "proof_status": "failed", "replay_gaps": 0,
            "semantic_category": "mixed_budget_boundary",
            "semantic_details": entry["expected_semantics"],
            "requested_samples": 3, "completed_samples": 3,
        }
        validate_result(entry, result)
        result["state"] = "timeout"
        with self.assertRaisesRegex(CorpusError, "censored result state"):
            validate_result(entry, result)


class ExistingSemanticManifestRegressionTests(unittest.TestCase):
    """Retain the earlier paired-runner/source-byte drift controls."""

    def test_legacy_runner_manifest_still_binds_fixture_bytes_and_metadata(self) -> None:
        benchmark_tests.validate_semantic_corpus_manifest(
            benchmark_tests.SEMANTIC_CORPUS_MANIFEST
        )

    def test_legacy_workload_identity_and_expectation_mutations_are_detected(self) -> None:
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

    def test_legacy_source_byte_change_is_rejected_with_original_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entries = benchmark_tests.SEMANTIC_CORPUS_MANIFEST
            for item in entries:
                destination = root / item["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / item["path"]).read_bytes())
            target = root / entries[0]["path"]
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "bytes/hash changed"):
                benchmark_tests.validate_semantic_corpus_manifest(entries, root=root)

    def test_legacy_replay_contract_mutation_is_detected(self) -> None:
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
