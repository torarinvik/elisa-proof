"""Reject ambiguous or non-standard JSON in compiler provenance metadata."""

from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strict_json import load, loads  # noqa: E402


class StrictJsonTests(unittest.TestCase):
    def test_accepts_standard_json(self) -> None:
        self.assertEqual(loads('{"compiler": {"revision": "abc"}, "count": 2}'),
                         {"compiler": {"revision": "abc"}, "count": 2})
        self.assertEqual(load(io.StringIO('[true, null, -1.25]')), [True, None, -1.25])

    def test_rejects_duplicate_keys_at_every_object_depth(self) -> None:
        for raw in ('{"revision": "first", "revision": "second"}',
                    '{"nested": {"revision": 1, "revision": 2}}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                loads(raw)

    def test_rejects_nonstandard_numeric_constants(self) -> None:
        for raw in ('NaN', 'Infinity', '-Infinity', '{"value": NaN}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "non-standard JSON numeric constant"):
                loads(raw)


if __name__ == "__main__":
    unittest.main()
