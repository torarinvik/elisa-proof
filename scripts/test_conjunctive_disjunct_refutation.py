"""Either denied conjunct refutes an AND; one denied OR branch does not."""
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
run = subprocess.run([binary, "--json", str(root / "examples/conjunctive_disjunct_refutation.elisa")],
                     capture_output=True, text=True, timeout=30)
assert run.returncode == 1, run.stderr
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
assert report["replay"]["replayed"] == report["replay"]["certificates"]
assert not report["trust"]["trusted_assumptions"]
assert {f["name"] for f in report["findings"]} == {
    "rejected_true_conjunction", "rejected_partial_disjunction"}
for name in ("false_left_conjunct", "false_right_conjunct", "denied_symbolic_conjunct"):
    assert any(d.get("name") == name and d.get("verified") for d in report["declaration_details"])
print("Denied AND conjuncts replay; true AND and partially denied OR reject")
