"""The focused regression runner must never silently use a stale proof executable."""

import ast
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import qualified_test_binary


ROOT = Path(__file__).resolve().parents[1]
QUALIFIED = ROOT / "build/elisa-proof-generations/current/elisa-proof"
STALE = ROOT / "build/elisa-proof"


class QualifiedProofBinaryTests(unittest.TestCase):
    def test_cli_regressions_do_not_default_to_build_binary(self):
        scripts = ROOT / "scripts"
        test_files = [*scripts.glob("test_*.py"), * (scripts / "tests").glob("test_*.py")]
        for path in test_files:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == "ELISA_PROOF_BIN"
                    and len(node.args) > 1
                ):
                    continue
                default_text = ast.get_source_segment(
                    source, node.args[1]
                ) or ""
                constants = {
                    child.value
                    for child in ast.walk(node.args[1])
                    if isinstance(child, ast.Constant) and isinstance(child.value, str)
                }
                self.assertFalse(
                    "build/elisa-proof" in default_text
                    or {"build", "elisa-proof"}.issubset(constants),
                    f"{path}:{node.lineno} defaults to an unqualified proof binary",
                )

    def test_standalone_resolves_current_product(self):
        result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"proof_binary": str(QUALIFIED)}), stderr=""
        )
        with patch.dict(os.environ, {}, clear=True), patch.object(
            qualified_test_binary.subprocess, "run", return_value=result
        ) as run:
            self.assertEqual(qualified_test_binary.proof_test_binary(ROOT), str(QUALIFIED))
        run.assert_called_once_with(
            ["bash", str(ROOT / "scripts/qualify_prebuilt_test.sh"), "--json"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )

    def test_standalone_rejects_explicit_stale_path(self):
        result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"proof_binary": str(QUALIFIED)}), stderr=""
        )
        with patch.dict(os.environ, {"ELISA_PROOF_BIN": str(STALE)}, clear=True), patch.object(
            qualified_test_binary.subprocess, "run", return_value=result
        ):
            with self.assertRaisesRegex(SystemExit, "not the current qualified product"):
                qualified_test_binary.proof_test_binary(ROOT)

    def test_failed_qualification_rejects_fallback(self):
        result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="source/product mismatch"
        )
        with patch.dict(os.environ, {}, clear=True), patch.object(
            qualified_test_binary.subprocess, "run", return_value=result
        ):
            with self.assertRaisesRegex(SystemExit, "refused an unqualified binary"):
                qualified_test_binary.proof_test_binary(ROOT)

    def test_matrix_marker_must_match_configured_path(self):
        environment = {
            "ELISA_PROOF_BIN": str(STALE),
            "ELISA_PROOF_QUALIFIED_BIN": str(QUALIFIED),
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(
            qualified_test_binary.subprocess, "run"
        ) as run:
            with self.assertRaisesRegex(SystemExit, "does not match ELISA_PROOF_BIN"):
                qualified_test_binary.proof_test_binary(ROOT)
        run.assert_not_called()

    def test_matrix_uses_matching_prequalified_path_without_resolving_again(self):
        environment = {
            "ELISA_PROOF_BIN": str(QUALIFIED),
            "ELISA_PROOF_QUALIFIED_BIN": str(QUALIFIED),
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(
            qualified_test_binary.subprocess, "run"
        ) as run:
            self.assertEqual(qualified_test_binary.proof_test_binary(ROOT), str(QUALIFIED))
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
