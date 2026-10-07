"""Pinned recipe inventories vary by revision and must remain inert data."""
import subprocess
import unittest
from unittest import mock

from compiler_recipe_inputs import committed_recipe_paths


class RecipeInputsTests(unittest.TestCase):
    def read(self, source):
        with mock.patch("compiler_recipe_inputs.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, stdout=source)) as run:
            result = committed_recipe_paths("repo", "pinned")
            self.assertEqual(run.call_args.args[0], ["git", "-C", "repo", "show",
                "pinned:scripts/stage1_provenance.py"])
            return result

    def test_inventory_tracks_exact_revision(self):
        for count in (4, 7):
            paths = tuple(f"scripts/recipe_{index}.sh" for index in range(count))
            self.assertEqual(self.read(f"BUILD_RECIPES = {paths!r}"), paths)

    def test_inventory_source_is_not_executed(self):
        self.assertEqual(self.read("raise RuntimeError('never execute')\n"
            "BUILD_RECIPES = ('scripts/build.sh',)"), ("scripts/build.sh",))

    def test_invalid_or_executable_inventory_is_rejected(self):
        for source in ("BUILD_RECIPES = get_paths()", "BUILD_RECIPES = ()",
                "BUILD_RECIPES = ['scripts/a']", "BUILD_RECIPES = ('../escape',)",
                "BUILD_RECIPES = ('scripts/../escape',)", "BUILD_RECIPES = ('scripts//a',)",
                "BUILD_RECIPES = ('scripts/a', 'scripts/a')", "BUILD_RECIPES = (3,)",
                "OTHER = ()", "BUILD_RECIPES = ('scripts/a',)\nBUILD_RECIPES = ('scripts/b',)"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.read(source)


if __name__ == "__main__":
    unittest.main()
