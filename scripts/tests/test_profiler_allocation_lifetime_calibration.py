#!/usr/bin/env python3
"""Calibrate profiler lifetime analysis on a deterministic synthetic capture."""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
PROFILER_ROOT = REPO.parent / "elisa-profiler"
ANALYZER = PROFILER_ROOT / "scripts" / "analyze-allocation-sites.py"
FIXTURE = Path(__file__).parent / "fixtures" / "profiler_allocation_lifetime_calibration.json"


def load_analyzer():
    if not ANALYZER.is_file():
        raise RuntimeError(f"elisa-profiler analyzer not found: {ANALYZER}")
    spec = importlib.util.spec_from_file_location("elisa_profiler_allocation_analyzer", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AllocationLifetimeCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = load_analyzer()
        cls.profile = json.loads(FIXTURE.read_text())

    def test_known_live_retired_and_retained_counts(self):
        result = self.analyzer.analyze(self.profile)
        repetition = result["repetitions"][0]

        self.assertEqual(repetition["lifetime_status"], "available")
        self.assertIsNone(repetition["lifetime_reason"])
        self.assertEqual(repetition["metrics"]["peak_logical_live_bytes"], 24)
        self.assertEqual(repetition["metrics"]["logical_live_bytes_at_capture_end"], 0)
        self.assertEqual(repetition["metrics"]["observed_backing_capacity_at_capture_end_bytes"], 64)
        self.assertEqual(repetition["metrics"]["max_retained_backing_capacity_after_reset_bytes"], 64)
        self.assertFalse(repetition["traffic_truncated"])
        self.assertEqual(len(repetition["sites"]), 1)
        self.assertEqual(repetition["sites"][0]["allocation_count"], 2)
        self.assertEqual(repetition["sites"][0]["retired_count"], 2)
        self.assertEqual(repetition["sites"][0]["max_observed_lifetime_ns"], 50)

    def test_each_reported_loss_indicator_withholds_lifetime_metrics(self):
        loss_fields = (
            "allocation_events_dropped",
            "frame_dropped",
            "trace_dropped",
            "capture_bytes_dropped",
            "trace_stack_overflow_entries",
        )
        for field in loss_fields:
            with self.subTest(field=field):
                profile = json.loads(json.dumps(self.profile))
                profile["run"]["repetitions"][0][field] = 1
                repetition = self.analyzer.analyze(profile)["repetitions"][0]
                self.assertEqual(repetition["lifetime_status"], "unavailable")
                self.assertEqual(repetition["lifetime_reason"], "capture loss or stack overflow")
                self.assertIsNone(repetition["metrics"])

    def test_incomplete_capture_withholds_lifetime_metrics(self):
        profile = json.loads(json.dumps(self.profile))
        profile["run"]["repetitions"][0]["capture_complete"] = False
        repetition = self.analyzer.analyze(profile)["repetitions"][0]
        self.assertEqual(repetition["lifetime_status"], "unavailable")
        self.assertEqual(repetition["lifetime_reason"], "incomplete capture")
        self.assertIsNone(repetition["metrics"])

    def test_analysis_bound_reports_truncation_and_withholds_metrics(self):
        profile = json.loads(json.dumps(self.profile))
        events = profile["run"]["repetitions"][0]["allocation_events"]
        profile["run"]["repetitions"][0]["allocation_events"] = events * (self.analyzer.LIMIT // len(events) + 1)
        repetition = self.analyzer.analyze(profile)["repetitions"][0]
        self.assertTrue(repetition["traffic_truncated"])
        self.assertEqual(repetition["lifetime_status"], "unavailable")
        self.assertEqual(repetition["lifetime_reason"], "analysis event bound exceeded")
        self.assertIsNone(repetition["metrics"])

    def test_analyzer_cli_emits_same_calibration_result(self):
        completed = subprocess.run(
            [sys.executable, str(ANALYZER), str(FIXTURE)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        repetition = result["repetitions"][0]
        self.assertEqual(repetition["lifetime_status"], "available")
        self.assertEqual(repetition["metrics"]["peak_logical_live_bytes"], 24)


if __name__ == "__main__":
    unittest.main()
