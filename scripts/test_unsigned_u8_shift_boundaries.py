"""Replay one valid u8 shift and refuse invalid-count and high-bit overreach."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/unsigned_u8_shift_boundaries.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
)
assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0, report["replay"]

functions = {
    declaration["name"]: declaration
    for declaration in report["declaration_details"]
    if declaration.get("kind") == "function"
}
assert functions["small_valid_left_shift"]["verified"], functions["small_valid_left_shift"]
refused = {
    "negative_shift_count_is_rejected",
    "shift_by_exact_width_is_not_assumed_zero",
    "high_bit_right_shift_is_not_reinterpreted_as_zero",
}
for name in refused:
    assert not functions[name]["verified"], (name, functions[name])

unproven = {
    goal["name"]
    for goal in report["goals"]
    if goal["rule"] == "goal" and not goal["proven"]
}
assert refused <= unproven, (refused, unproven)
findings = {(finding["name"], finding["kind"]) for finding in report["findings"]}
assert all((name, "ensure-unproven") in findings for name in refused), findings
negative_diagnostics = [
    diagnostic
    for diagnostic in report["semantic_diagnostics"]
    if diagnostic["message"] == "shift count is negative"
]
assert [(diagnostic["line"], diagnostic["severity"]) for diagnostic in negative_diagnostics] == [(11, 2)], report["semantic_diagnostics"]
print("u8 shifts: valid small shift replays; negative, width-sized, and high-bit overreach refuse")
