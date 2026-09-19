"""The watchdog must never turn malformed output or a crashed prover into completion."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALID = {
    "status": "proved",
    "verification_state": "proved",
    "summary": {"obligations": 1, "proven": 1, "failed": 0, "semantic_errors": 0},
    "replay": {"certificates": 1, "replayed": 1, "gaps": 0},
}


class AuditHarnessTests(unittest.TestCase):
    def run_audit(self, report=VALID, exit_code=0, time_limit="5", delay="0", raw=None):
        with tempfile.TemporaryDirectory(prefix="elisa-audit-test-") as directory:
            work = Path(directory)
            binary = work / "prover"
            binary.write_text(
                f"#!{sys.executable}\n"
                "import os, sys, time\n"
                "time.sleep(float(os.environ['AUDIT_TEST_DELAY']))\n"
                "print(os.environ['AUDIT_TEST_REPORT'], flush=True)\n"
                "sys.exit(int(os.environ['AUDIT_TEST_EXIT']))\n",
                encoding="utf-8",
            )
            binary.chmod(0o700)
            env = dict(os.environ)
            env.update(
                ELISA_FULL_AUDIT_BINARY=str(binary),
                ELISA_FULL_AUDIT_SOURCE="examples/verified.elisa",
                ELISA_FULL_AUDIT_DIR=str(work / "artifacts"),
                ELISA_FULL_AUDIT_TIME_LIMIT=time_limit,
                ELISA_FULL_AUDIT_RSS_LIMIT_KB="1500000",
                AUDIT_TEST_REPORT=json.dumps(report) if raw is None else raw,
                AUDIT_TEST_EXIT=str(exit_code),
                AUDIT_TEST_DELAY=delay,
            )
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/audit_full_source.sh")],
                env=env, capture_output=True, text=True, timeout=10,
            )
            return result, json.loads(result.stdout) if result.stdout else None

    def test_complete_proved_and_failed_reports(self):
        result, audit = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(audit["complete"])
        failed = copy.deepcopy(VALID)
        failed.update(status="failed", verification_state="unsupported")
        failed["summary"].update(proven=0, failed=1)
        failed["replay"].update(certificates=0, replayed=0)
        result, audit = self.run_audit(failed, 1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(audit["complete"])
        self.assertEqual(audit["report_status"], "failed")

    def test_exit_must_agree_with_report(self):
        for exit_code in (1, 7, 139):
            with self.subTest(exit_code=exit_code):
                result, audit = self.run_audit(exit_code=exit_code)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(audit["complete"])
                self.assertIn("mismatch", audit["report_error"])

    def test_malformed_report_envelopes(self):
        reports = [None, [], {}, {"status": []}, {"status": "proved"}]
        for section, field, value in (
            ("summary", "proven", 2), ("summary", "proven", True),
            ("summary", "failed", -1), ("summary", "semantic_errors", 1),
            ("summary", "obligations", "1"), ("replay", "replayed", 0),
        ):
            report = copy.deepcopy(VALID)
            report[section][field] = value
            reports.append(report)
        for report in reports:
            with self.subTest(report=report):
                result, audit = self.run_audit(report)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(audit["complete"])
                self.assertIn("report_error", audit)

    def test_partial_json_is_incomplete(self):
        result, audit = self.run_audit(raw='{"status":"proved"')
        self.assertEqual(result.returncode, 2)
        self.assertFalse(audit["complete"])
        self.assertIn("parse_error", audit)

    def test_replay_gap_report_is_complete_but_not_proved(self):
        report = copy.deepcopy(VALID)
        report.update(status="proved_with_replay_gaps", verification_state="unknown")
        report["replay"].update(replayed=0, gaps=1)
        result, audit = self.run_audit(report, 1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(audit["complete"])
        self.assertEqual(audit["replay_gaps"], 1)
        self.assertEqual(audit["report_verification_state"], "unknown")

    def test_finite_positive_limits_required(self):
        for limit in ("nan", "inf", "-inf", "0", "-1"):
            with self.subTest(limit=limit):
                result, audit = self.run_audit(time_limit=limit)
                self.assertEqual(result.returncode, 2)
                self.assertIsNone(audit)
                self.assertIn("finite and positive", result.stderr)

    def test_timeout_remains_incomplete(self):
        result, audit = self.run_audit(time_limit="0.05", delay="2")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertFalse(audit["complete"])
        self.assertEqual(audit["stop_reason"], "time-limit")


if __name__ == "__main__":
    unittest.main()
