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

    def test_nested_store_resets_keep_lifetimes_and_sites_separate(self):
        profile = {
            "locations": [
                {"kind": "function", "identity_id": 11, "repetition": 1, "compiler_line": 0,
                 "function": "outer_store_alloc",
                 "source": "src/proof/outer_store.elisa"},
                {"kind": "function", "identity_id": 22, "repetition": 1, "compiler_line": 0,
                 "function": "inner_store_alloc",
                 "source": "src/proof/inner_store.elisa"},
                {"kind": "location", "identity_id": 11, "repetition": 1,
                 "compiler_line": 100, "source": "src/proof/outer_store.elisa", "line": 12},
                {"kind": "location", "identity_id": 22, "repetition": 1,
                 "compiler_line": 200, "source": "src/proof/inner_store.elisa", "line": 18},
            ],
            "run": {"repetitions": [{
                "repetition": 1,
                "capture_complete": True,
                "timed_out": False,
                "detail_budget_exceeded": False,
                "allocation_events_dropped": 0,
                "frame_dropped": 0,
                "trace_dropped": 0,
                "capture_bytes_dropped": 0,
                "trace_stack_overflow_entries": 0,
                "allocation_events": [
                    {"kind": "region_create", "arena": 7, "region": 0,
                     "address": 4096, "size_bytes": 128, "sequence": 0, "timestamp_ns": 10},
                    {"kind": "alloc", "arena": 7, "region": 0, "address": 8192,
                     "size_bytes": 8, "sequence": 1, "timestamp_ns": 20,
                     "repetition": 1, "site_stack": "11:100"},
                    {"kind": "region_create", "arena": 9, "region": 0,
                     "address": 12288, "size_bytes": 64, "sequence": 2, "timestamp_ns": 30},
                    {"kind": "alloc", "arena": 9, "region": 0, "address": 16384,
                     "size_bytes": 16, "sequence": 3, "timestamp_ns": 40,
                     "repetition": 1, "site_stack": "22:200"},
                    {"kind": "region_reset", "arena": 9, "region": 0,
                     "address": 0, "size_bytes": 0, "sequence": 4, "timestamp_ns": 70},
                    {"kind": "region_reset", "arena": 7, "region": 0,
                     "address": 0, "size_bytes": 0, "sequence": 5, "timestamp_ns": 100},
                ],
            }]},
        }

        repetition = self.analyzer.analyze(profile)["repetitions"][0]
        self.assertEqual(repetition["lifetime_status"], "available")
        self.assertEqual(repetition["metrics"]["peak_logical_live_bytes"], 24)
        self.assertEqual(repetition["metrics"]["logical_live_bytes_at_capture_end"], 0)
        sites = {site["function"]: site for site in repetition["sites"]}
        self.assertEqual(set(sites), {"outer_store_alloc", "inner_store_alloc"})
        self.assertEqual(sites["inner_store_alloc"]["source"], "src/proof/inner_store.elisa")
        self.assertEqual(sites["inner_store_alloc"]["line"], 18)
        self.assertEqual(sites["inner_store_alloc"]["retired_count"], 1)
        self.assertEqual(sites["inner_store_alloc"]["max_observed_lifetime_ns"], 30)
        self.assertEqual(sites["outer_store_alloc"]["source"], "src/proof/outer_store.elisa")
        self.assertEqual(sites["outer_store_alloc"]["line"], 12)
        self.assertEqual(sites["outer_store_alloc"]["retired_count"], 1)
        self.assertEqual(sites["outer_store_alloc"]["max_observed_lifetime_ns"], 80)

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
