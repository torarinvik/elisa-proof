#!/usr/bin/env python3
"""Focused checks for bounded allocation capture summarization."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from perf_luna_allocation_summary import CaptureError, load_artifact, summarize_allocation_captures


def record(*, complete: bool = True, dropped: int = 0) -> dict:
    return {
        "repetition": 1,
        "exit_code": 0,
        "capture_complete": complete,
        "allocation_events_dropped": dropped,
        "event_counts": {"alloc": 3, "region_create": 1, "region_free": 1},
        "lifetime_status": "available",
        "metrics": {
            "peak_logical_live_bytes": 96,
            "logical_live_bytes_at_capture_end": 0,
            "peak_observed_backing_capacity_bytes": 4096,
            "observed_backing_capacity_at_capture_end_bytes": 0,
        },
    }


class AllocationSummaryTests(unittest.TestCase):
    def test_keeps_live_bytes_capacity_and_quality_distinct(self) -> None:
        result = summarize_allocation_captures({"probe": [record()]})
        run = result["workloads"][0]["runs"][0]
        self.assertEqual(run["capture_quality"], "complete")
        self.assertEqual(run["event_counts"]["alloc"], 3)
        self.assertEqual(run["metrics"]["peak_logical_live_bytes"], 96)
        self.assertEqual(run["metrics"]["peak_observed_backing_capacity_bytes"], 4096)
        self.assertIn("not present", result["metric_notes"]["process_rss"])

    def test_marks_dropped_and_truncated_captures_incomplete(self) -> None:
        dropped = summarize_allocation_captures({"probe": [record(dropped=2)]})
        truncated = summarize_allocation_captures({"probe": [record(complete=False)]})
        self.assertEqual(dropped["workloads"][0]["runs"][0]["capture_quality"], "incomplete")
        self.assertEqual(dropped["workloads"][0]["runs"][0]["allocation_events_dropped"], 2)
        self.assertEqual(truncated["workloads"][0]["runs"][0]["capture_quality"], "incomplete")

    def test_rejects_malformed_counts_and_reads_artifact_envelope(self) -> None:
        malformed = record()
        malformed["event_counts"]["alloc"] = True
        with self.assertRaises(CaptureError):
            summarize_allocation_captures({"probe": [malformed]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            path.write_text(json.dumps({"allocation_captures": {"probe": [record()]}}),
                            encoding="utf-8")
            self.assertEqual(load_artifact(path)["workloads"][0]["workload"], "probe")


if __name__ == "__main__":
    unittest.main()
