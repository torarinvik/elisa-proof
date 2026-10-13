"""Replay harnesses may use only the Stage0 revision pinned by this proof checkout."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from source_binding_harness_support import checked_in_stage0_revision


ROOT = Path(__file__).resolve().parents[1]
PIN = (ROOT / "ELISA_STAGE0_REV").read_text(encoding="ascii").strip()


class CheckedInStage0RevisionTests(unittest.TestCase):
    def test_uses_checked_in_pin_without_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(checked_in_stage0_revision(ROOT), PIN)

    def test_accepts_matching_override(self):
        with patch.dict(os.environ, {"ELISA_STAGE0_REV": PIN}, clear=True):
            self.assertEqual(checked_in_stage0_revision(ROOT), PIN)

    def test_rejects_conflicting_override(self):
        conflicting = "0" * 40 if PIN != "0" * 40 else "1" * 40
        with patch.dict(os.environ, {"ELISA_STAGE0_REV": conflicting}, clear=True):
            with self.assertRaisesRegex(ValueError, "differs from the checked-in proof pin"):
                checked_in_stage0_revision(ROOT)


if __name__ == "__main__":
    unittest.main()
