"""Focused regression tests for the durable A21 evidence validator."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_a21_failure_classification as a21  # noqa: E402


class A21FailureClassificationTests(unittest.TestCase):
    def test_committed_classification_is_valid(self) -> None:
        self.assertEqual(a21.validate(), [])

    def test_validator_rejects_changed_event_classification(self) -> None:
        original = a21.LEDGER.read_text(encoding="utf-8")
        changed = original.replace("19\tstep\t45\tREPLAY\t", "19\tstep\t45\tOPEN\t", 1)
        self.assertNotEqual(changed, original)
        with tempfile.TemporaryDirectory() as directory:
            altered_ledger = Path(directory) / "events.tsv"
            altered_ledger.write_text(changed, encoding="utf-8")
            with patch.object(a21, "LEDGER", altered_ledger):
                errors = a21.validate()
        self.assertTrue(any("classification counts differ" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
