"""Negated conjunctions from guarded-return fall-through replay as case splits."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/negated_conjunction_fallthrough.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
)
assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0, report
assert report["replay"]["gaps"] == 0, report
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0, report
functions = {
    declaration["name"]: declaration
    for declaration in report["declaration_details"]
    if declaration.get("kind") == "function"
}
assert functions["guarded_selector"]["verified"], functions["guarded_selector"]
assert functions["de_morgan_case"]["verified"], functions["de_morgan_case"]
assert not functions["false_negated_conjunction_control"]["verified"], functions["false_negated_conjunction_control"]
assert not any(
    goal["name"] in ("guarded_selector", "de_morgan_case") and not goal["proven"]
    for goal in report["goals"]
), report["goals"]
assert any(
    goal["name"] == "false_negated_conjunction_control" and not goal["proven"]
    for goal in report["goals"]
), report["goals"]
print("negated conjunction fall-through: selector contracts replay; false control remains rejected")
