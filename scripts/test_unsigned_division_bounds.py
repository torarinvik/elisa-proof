"""Replay unsigned quotient bounds and refuse width, sign, and overflow overreach."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/unsigned_division_bounds.elisa")],
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
positive_names = (
    "quotient_below_dividend",
    "quotient_by_positive_literal_below_dividend",
    "high_bit_u64_quotient_below_dividend",
)
for name in positive_names:
    assert functions[name]["verified"], (name, functions[name])
negative_names = (
    "mismatched_divisor_width_not_inferred",
    "zero_divisor_not_assumed_positive",
    "quotient_plus_dividend_does_not_wrap",
    "quotient_below_unrelated_ceiling_is_not_inferred",
    "signed_negative_quotient_does_not_use_unsigned_order",
)
findings = {
    (finding["name"], finding["kind"])
    for finding in report["findings"]
}
for name in negative_names:
    assert not functions[name]["verified"], (name, functions[name])
    assert any(goal["name"] == name and not goal["proven"] for goal in report["goals"]), name
    assert (name, "ensure-unproven") in findings, (name, report["findings"])
print("unsigned division: quotient bounds replay; width, signedness, and wrapping overreach stay open")
