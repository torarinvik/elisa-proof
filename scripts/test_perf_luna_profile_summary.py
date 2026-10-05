#!/usr/bin/env python3
"""Synthetic tests for the bounded Luna profiler capture summarizer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from perf_luna_profile_summary import (
    MAX_IDENTITY_ID,
    CaptureError,
    load_capture,
    summarize_capture,
)


def capture_fixture() -> dict:
    return {
        "schema_version": 2,
        "envelope": {"kind": "profile"},
        "source": "example.elisa",
        "summary": {
            "capture_complete": True,
            "sample_count": 4,
            "sample_missed": 0,
            "sample_period_microseconds": 1000,
            "sampling_setup_failed": 0,
            "dropped": 0,
            "frame_dropped": 0,
            "capture_bytes_dropped": 0,
            "stack_overflow_entries": 0,
        },
        "run": {
            "collection_mode": "sample",
            "outcome": "success",
            "requested_repetitions": 1,
            "completed_repetitions": 1,
        },
        "samples": [
            {"stack": "main;alpha;leaf", "repetition": 1},
            {"stack": "main;alpha;leaf", "repetition": 1},
            {"stack": "main;beta", "repetition": 1},
            {"stack": "main;alpha", "repetition": 1},
        ],
        "program_stdout_truncated": False,
        "program_stderr_truncated": False,
        "functions": [
            {"function": "main", "identity_id": "10", "repetition": 1},
            {"function": "alpha", "identity_id": "11", "repetition": 1},
            {"function": "leaf", "identity_id": "12", "repetition": 1},
            {"function": "beta", "identity_id": "13", "repetition": 1},
        ],
        "locations": [
            {"kind": "function", "function": "alpha", "identity_id": "11",
             "repetition": 1, "source": "lib/a.elisa", "compiler_line": 30, "line": 7},
        ],
    }


class ProfileSummaryTests(unittest.TestCase):
    def test_ranks_leaf_and_inclusive_frames_with_identity_definition(self) -> None:
        result = summarize_capture(capture_fixture(), top=10)
        self.assertEqual(result["capture"]["sample_quality"], "complete")
        self.assertTrue(result["capture"]["complete_measurement_accepted"])
        self.assertEqual(result["rankings"]["leaf_frames"][0], {
            "name": "leaf", "samples": 2, "share_percent": 50.0,
        })
        inclusive = {row["name"]: row["samples"]
                     for row in result["rankings"]["inclusive_frames"]}
        self.assertEqual(inclusive, {"main": 4, "alpha": 3, "leaf": 2, "beta": 1})
        inclusive_shares = {row["name"]: row["share_percent"]
                             for row in result["rankings"]["inclusive_frames"]}
        self.assertEqual(inclusive_shares["main"], 100.0)
        alpha = next(row for row in result["definitions"] if row["name"] == "alpha")
        self.assertEqual(alpha["identity_id"], "11")
        self.assertEqual(alpha["samples"], 3)
        self.assertEqual(alpha["definitions"], [{
            "source": "lib/a.elisa", "compiler_line": 30, "line": 7,
        }])

    def test_recursive_stack_counts_name_once_per_sample(self) -> None:
        data = capture_fixture()
        data["samples"] = [
            {"stack": "main;recur;recur;leaf", "repetition": 1},
            {"stack": "main;recur;leaf", "repetition": 1},
        ]
        data["summary"]["sample_count"] = 2
        rows = {row["name"]: row for row in
                summarize_capture(data)["rankings"]["inclusive_frames"]}
        self.assertEqual(rows["recur"]["samples"], 2)
        self.assertEqual(rows["recur"]["share_percent"], 100.0)
        self.assertEqual(rows["main"]["samples"], 2)
        self.assertEqual(rows["leaf"]["samples"], 2)

    def test_name_collision_keeps_identities_and_refuses_sample_attribution(self) -> None:
        data = capture_fixture()
        data["functions"].extend([
            {"function": "alpha", "identity_id": "99", "repetition": 1},
        ])
        data["locations"].append({
            "kind": "function", "function": "alpha", "identity_id": "99",
            "repetition": 1, "source": "other/a.elisa", "compiler_line": 80, "line": 9,
        })
        rows = [row for row in summarize_capture(data)["definitions"]
                if row["name"] == "alpha"]
        self.assertEqual({row["identity_id"] for row in rows}, {"11", "99"})
        self.assertTrue(all(row["samples"] is None for row in rows))
        self.assertTrue(all(row["attribution"] == "ambiguous_name_collision" for row in rows))

    def test_identity_ids_are_ascii_positive_uint64(self) -> None:
        data = capture_fixture()
        data["functions"][0]["identity_id"] = str(MAX_IDENTITY_ID)
        result = summarize_capture(data)
        self.assertIn(str(MAX_IDENTITY_ID), {
            row["identity_id"] for row in result["definitions"]
        })
        for invalid in ("", "0", "٠", "１２", "1\u0661", str(MAX_IDENTITY_ID + 1),
                        MAX_IDENTITY_ID + 1, 0, -1, True):
            with self.subTest(invalid=repr(invalid)):
                bad = capture_fixture()
                bad["functions"][0]["identity_id"] = invalid
                with self.assertRaises(CaptureError):
                    summarize_capture(bad)

    def test_missing_identity_with_multiple_source_definitions_is_ambiguous(self) -> None:
        data = capture_fixture()
        data["functions"].append({"function": "alpha", "repetition": 1})
        data["functions"][1].pop("identity_id")
        data["locations"] = [
            {"kind": "function", "function": "alpha", "repetition": 1,
             "source": "first.elisa", "compiler_line": 1, "line": 1},
            {"kind": "function", "function": "alpha", "repetition": 1,
             "source": "second.elisa", "compiler_line": 2, "line": 2},
        ]
        rows = [row for row in summarize_capture(data)["definitions"]
                if row["name"] == "alpha"]
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["identity_id"])
        self.assertIsNone(rows[0]["samples"])
        self.assertEqual(rows[0]["attribution"], "ambiguous_name_collision")

    def test_partial_capture_reports_all_loss_and_count_discrepancies(self) -> None:
        data = capture_fixture()
        data["summary"].update({
            "capture_complete": False,
            "sample_count": 5,
            "sample_missed": 2,
            "sampling_setup_failed": 1,
            "dropped": 3,
            "frame_dropped": 1,
            "capture_bytes_dropped": 4,
            "stack_overflow_entries": 2,
        })
        data["run"]["completed_repetitions"] = 0
        quality = summarize_capture(data)["capture"]
        self.assertEqual(quality["sample_quality"], "degraded")
        self.assertEqual(quality["reported_samples"], 5)
        self.assertEqual(quality["retained_sample_records"], 4)
        self.assertEqual(quality["sample_missed"], 2)
        self.assertEqual(quality["sampling_setup_failed"], 1)
        self.assertEqual(quality["dropped"]["total"], 10)
        self.assertEqual(set(quality["quality_reasons"]), {
            "capture_incomplete", "sample_count_mismatch", "samples_missed",
            "sampling_setup_failed", "capture_records_dropped_or_overflowed",
            "repetitions_incomplete",
        })

    def test_event_loss_refuses_complete_measurement_even_if_runtime_says_complete(self) -> None:
        data = capture_fixture()
        # Contradict the producer's completion bit while keeping the retained
        # sample count consistent: one overflow alone must close the gate.
        data["summary"]["stack_overflow_entries"] = 1
        quality = summarize_capture(data)["capture"]
        self.assertTrue(quality["complete"])
        self.assertEqual(quality["sample_quality"], "degraded")
        self.assertFalse(quality["complete_measurement_accepted"])
        self.assertEqual(quality["quality_reasons"], [
            "capture_records_dropped_or_overflowed",
        ])

    def test_malformed_capture_and_malformed_sample_are_rejected_or_reported(self) -> None:
        with self.assertRaisesRegex(CaptureError, "schema_version"):
            summarize_capture({})
        data = capture_fixture()
        data["samples"].append({"stack": "main;;broken", "repetition": 1})
        data["summary"]["sample_count"] = 5
        result = summarize_capture(data)
        self.assertEqual(result["capture"]["malformed_sample_records"], 1)
        self.assertIn("malformed_sample_records", result["capture"]["quality_reasons"])

    def test_truncated_stdout_does_not_invalidate_samples_or_claim_proof_verification(self) -> None:
        data = capture_fixture()
        data["program_stdout_truncated"] = True
        result = summarize_capture(data)
        self.assertEqual(result["capture"]["sample_quality"], "complete")
        self.assertEqual(result["capture"]["valid_sample_records"], 4)
        self.assertTrue(result["rankings"]["leaf_frames"])
        self.assertEqual(result["proof_verification"], {
            "status": "unavailable_output_truncated",
            "verified": False,
            "program_stdout_truncated": True,
            "program_stderr_truncated": False,
        })

    def test_json_loader_refuses_malformed_and_oversized_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            path.write_text('{"partial":', encoding="utf-8")
            with self.assertRaisesRegex(CaptureError, "parse capture JSON"):
                load_capture(path)
            path.write_text(json.dumps(capture_fixture()), encoding="utf-8")
            with self.assertRaisesRegex(CaptureError, "limit"):
                load_capture(path, max_bytes=8)
            self.assertEqual(load_capture(path, max_bytes=path.stat().st_size)["schema_version"], 2)
            with self.assertRaisesRegex(CaptureError, "positive integer"):
                load_capture(path, max_bytes=0)

    def test_ranking_limit_is_bounded(self) -> None:
        with self.assertRaisesRegex(CaptureError, "between 1 and 500"):
            summarize_capture(capture_fixture(), top=501)


if __name__ == "__main__":
    unittest.main()
