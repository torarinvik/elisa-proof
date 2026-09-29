"""Distinct in-range constants justify a narrow unsigned disequality disjunction."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name: str, expected_exit: int) -> dict:
    run = subprocess.run([str(BINARY), "--json", str(ROOT / f"examples/{name}.elisa")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected_exit, (name, run.returncode, run.stderr, run.stdout)
    return json.loads(run.stdout)


positive = report("unsigned_equal_constant_exclusion", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert positive["summary"]["semantic_errors"] == positive["summary"]["semantic_diagnostics"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] == positive["summary"]["proven"], positive
assert positive["replay"]["gaps"] == 0 and positive["trust"]["trusted_assumptions"] == [], positive
function = next(item for item in positive["declaration_details"]
                if item.get("name") == "distinct_constants_from_u8")
assert function["verified"] and function["ensures"] == 2, function

negative = report("rejected_same_constant_disequality", 1)
assert negative["status"] == "failed" and negative["verification_state"] == "disproved", negative
assert negative["summary"]["semantic_errors"] == 0, negative
assert [item["message"] for item in negative["semantic_diagnostics"]] == [
    'identical operands on both sides of "or"'
], negative
assert negative["replay"]["gaps"] == 0, negative
assert any(finding["kind"] == "ensure-unproven" and finding["status"] == "disproved"
           and finding["counterexample_found"] for finding in negative["findings"]), negative

print("unsigned disequality disjunctions: distinct in-range constants replay; repeated constant refuted")
