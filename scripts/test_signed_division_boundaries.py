"""Replay safe signed division and refuse zero-divisor and MIN/-1 boundaries."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/signed_division_boundaries.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
)
assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0, report["replay"]

positive = {"safe_division_by_negative_one", "safe_remainder_by_negative_two"}
negative = {
    "minimum_division_by_negative_one_is_not_assumed_safe",
    "minimum_remainder_by_negative_one_is_not_assumed_safe",
    "division_by_zero_is_rejected",
    "remainder_by_zero_is_rejected",
}
functions = {
    declaration["name"]: declaration
    for declaration in report["declaration_details"]
    if declaration.get("kind") == "function"
}
for name in positive:
    assert functions[name]["verified"], (name, functions[name])
for name in negative:
    assert not functions[name]["verified"], (name, functions[name])

unproven = {
    goal["name"]
    for goal in report["goals"]
    if goal["rule"] == "goal" and not goal["proven"]
}
assert negative <= unproven, (negative, unproven)
findings = {(finding["name"], finding["kind"]) for finding in report["findings"]}
for name in negative:
    assert (name, "ensure-unproven") in findings, (name, findings)

zero_diagnostics = {
    diagnostic["line"]: diagnostic["message"]
    for diagnostic in report["semantic_diagnostics"]
    if diagnostic["message"] in {"division by zero", "modulo by zero"}
}
assert zero_diagnostics == {31: "division by zero", 35: "modulo by zero"}, report["semantic_diagnostics"]
print("signed division boundaries: safe cases replay; minimum overflow and zero-divisor controls refuse")
