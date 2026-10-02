"""Checked De Morgan goal transformation with independently replayed controls."""
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
run = subprocess.run([binary, "--json", str(root / "examples/negated_whitespace_recognition_gap.elisa")],
                     capture_output=True, text=True, timeout=30)
assert run.returncode == 1, run.stderr
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
assert report["replay"]["replayed"] == report["replay"]["certificates"]
assert not report["trust"]["trusted_assumptions"]
assert {f["name"] for f in report["findings"]} == {
    "rejected_ascii_whitespace_exclusion", "rejected_half_disjunction_denial", "rejected_true_conjunction_denial"}
for name in ("nonascii_excludes_ascii_whitespace", "negated_boolean_conjunction", "negated_boolean_disjunction"):
    assert any(d.get("name") == name and d.get("verified") for d in report["declaration_details"])
print("Nested negated goals replay; true ASCII, half-denied OR and true AND controls reject")
