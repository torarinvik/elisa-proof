"""Adversarial tests for the source-identity-bound kernel-core dogfood inventory."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / "build" / "elisa-proof"
INVENTORY = ROOT / "scripts" / "dogfood_kernel_core_inventory.json"
CHECKER = ROOT / "scripts" / "check_dogfood_kernel_core_inventory.py"


class DogfoodKernelCoreInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PROOF.is_file():
            raise RuntimeError("build elisa-proof before running this inventory test")
        cls.reports = {}
        for slice_name, source in (
            ("kernel_core", ROOT / "src" / "proof" / "kernel_core.elisa"),
            ("kernel_core_fixture", ROOT / "examples" / "dogfood_kernel_core.elisa"),
        ):
            completed = subprocess.run([str(PROOF), "--json", str(source)], check=False,
                                       capture_output=True, text=True)
            if completed.returncode != 0:
                raise RuntimeError(f"proof producer failed for {slice_name}: {completed.stderr}")
            cls.reports[slice_name] = json.loads(completed.stdout)

    def run_gate(self, root: Path, report: dict, slice_name: str) -> subprocess.CompletedProcess[str]:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as report_file:
            json.dump(report, report_file)
            report_file.flush()
            return subprocess.run(
                [sys.executable, str(CHECKER), "--root", str(root), "--report", report_file.name,
                 "--inventory", str(INVENTORY), "--slice", slice_name],
                capture_output=True, text=True, check=False,
            )

    def test_current_core_and_fixture_have_exact_inventories(self) -> None:
        for slice_name in ("kernel_core", "kernel_core_fixture"):
            with self.subTest(slice=slice_name):
                result = self.run_gate(ROOT, self.reports[slice_name], slice_name)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_tautological_source_mutation_is_rejected_even_with_original_totals(self) -> None:
        report = self.reports["kernel_core_fixture"]
        with tempfile.TemporaryDirectory() as directory:
            altered_root = Path(directory)
            for relative in ("src/proof/kernel_core.elisa", "examples/dogfood_kernel_core.elisa"):
                target = altered_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            source = altered_root / "src/proof/kernel_core.elisa"
            contents = source.read_text(encoding="utf-8")
            contents = contents.replace(
                "ensure result == (root < node_count)", "ensure result == true", 1)
            source.write_text(contents, encoding="utf-8")
            result = self.run_gate(altered_root, report, "kernel_core_fixture")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source identity mismatch", result.stderr)
            self.assertEqual(report["summary"]["obligations"], 50)
            self.assertEqual(report["summary"]["proven"], 50)

    def test_omitted_property_and_declaration_cannot_be_replaced_to_preserve_totals(self) -> None:
        original = self.reports["kernel_core_fixture"]
        forged = copy.deepcopy(original)
        omitted_declaration = next(
            item for item in forged["declaration_details"]
            if item.get("kind") == "function" and item.get("name") == "direct_depth_contract")
        forged["declaration_details"].remove(omitted_declaration)
        replacement = copy.deepcopy(next(
            item for item in forged["declaration_details"]
            if item.get("kind") == "function" and item.get("name") == "direct_root_contract"))
        replacement["name"] = "unrelated_proved_helper"
        forged["declaration_details"].append(replacement)

        omitted_goal = next(
            item for item in forged["goals"]
            if item.get("rule") == "goal" and item.get("name") == "direct_depth_contract")
        forged["goals"].remove(omitted_goal)
        goal_replacement = copy.deepcopy(next(
            item for item in forged["goals"]
            if item.get("rule") == "goal" and item.get("name") == "direct_root_contract"))
        goal_replacement["name"] = "unrelated_proved_helper"
        forged["goals"].append(goal_replacement)

        self.assertEqual(forged["summary"], original["summary"])
        self.assertEqual(len(forged["declaration_details"]), len(original["declaration_details"]))
        self.assertEqual(sum(goal["proven"] for goal in forged["goals"]),
                         sum(goal["proven"] for goal in original["goals"]))
        result = self.run_gate(ROOT, forged, "kernel_core_fixture")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inventory", result.stderr)


if __name__ == "__main__":
    unittest.main()
