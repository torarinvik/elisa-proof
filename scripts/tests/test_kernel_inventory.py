"""Adversarial checks for the trusted kernel's source-level dependency boundary."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from test_kernel_inventory import (  # noqa: E402
    kernel_call_target_violations,
    kernel_source_files,
)


class KernelCallClosureTests(unittest.TestCase):
    def test_kernel_source_set_follows_the_replay_facade_includes(self) -> None:
        names = {path.name for path in kernel_source_files()}
        self.assertTrue({
            "kernel_core.elisa", "kernel_replay.elisa", "kernel_typed_literals.elisa",
            "kernel_typed_arithmetic.elisa", "kernel_contextual_constants.elisa",
            "api.elisa",
        } <= names)

    def check_source(self, source: str) -> set[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kernel.elisa"
            path.write_text(source, encoding="utf-8")
            return kernel_call_target_violations([path])

    def test_local_and_kernel_module_calls_are_allowed(self) -> None:
        core = """module ElisaProofKernelCore:
    public:
        def helper() -> bool:
            return true
"""
        replay = """extend ElisaProofKernelReplay:
    private:
        def local_helper() -> bool:
            return true
        def checked() -> bool:
            return local_helper() and ElisaProofKernelCore::helper()
"""
        with tempfile.TemporaryDirectory() as directory:
            core_path = Path(directory) / "core.elisa"
            replay_path = Path(directory) / "replay.elisa"
            core_path.write_text(core, encoding="utf-8")
            replay_path.write_text(replay, encoding="utf-8")
            self.assertEqual(
                kernel_call_target_violations([core_path, replay_path]), set(),
            )

    def test_unqualified_and_qualified_external_calls_are_rejected(self) -> None:
        source = """extend ElisaProofKernelReplay:
    private:
        def checked() -> bool:
            foreign_helper()
            Outside::escape()
            return true
"""
        self.assertEqual(
            self.check_source(source),
            {"ElisaProofKernelReplay::foreign_helper", "Outside::escape"},
        )

    def test_comments_strings_and_expression_operators_are_not_calls(self) -> None:
        source = '''extend ElisaProofKernelReplay:
    private:
        # foreign_helper() and Outside::escape()
        def checked() -> bool:
            text: sview = "foreign_helper() # Outside::escape()"
            flag: bool = not (true and false)
            pair: mutable (bool, i64) = (flag, 0)
            return flag
'''
        self.assertEqual(self.check_source(source), set())


if __name__ == "__main__":
    unittest.main()
