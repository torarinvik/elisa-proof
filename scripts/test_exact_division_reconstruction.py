"""Replay exact integer quotient reconstruction and reject missing or mismatched premises."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

BINARY = Path(qualified_test_binary.proof_test_binary(ROOT))
run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/exact_division_reconstruction.elisa")],
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
positive = {
    "unsigned_division_reconstructs_exact_multiple",
    "signed_positive_division_reconstructs_exact_multiple",
    "signed_negative_division_reconstructs_exact_multiple",
}
refused = {
    "missing_zero_remainder_does_not_prove_reconstruction",
    "nonzero_remainder_does_not_prove_reconstruction",
    "a_different_multiplier_does_not_reconstruct",
}
assert all(functions[name]["verified"] for name in positive), functions
assert not any(functions[name]["verified"] for name in refused), functions
findings = {
    (finding["name"], finding["kind"])
    for finding in report["findings"]
}
assert all((name, "ensure-unproven") in findings for name in refused), findings
print("exact division reconstruction replays; missing and mismatched premises stay open")
