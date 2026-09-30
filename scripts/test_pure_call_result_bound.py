"""Bound a verified pure call result, but keep opaque call results unsupported."""
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


positive = report("pure_call_result_bound", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert positive["summary"]["semantic_errors"] == positive["summary"]["semantic_diagnostics"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] == positive["summary"]["proven"], positive
assert positive["replay"]["gaps"] == 0 and positive["trust"]["trusted_assumptions"] == [], positive
call_bound = next(goal for goal in positive["goals"]
                  if goal["name"] == "caller_action_bound" and goal["goal"].get("operator") == "<=")
assert call_bound["proven"] and any(origin and origin["kind"] == "function-summary"
                                    for origin in call_bound["fact_origins"]), call_bound

negative = report("rejected_opaque_call_result_bound", 1)
assert negative["status"] == "failed" and negative["summary"]["failed"] > 0, negative
assert negative["summary"]["semantic_errors"] == negative["summary"]["semantic_diagnostics"] == 0, negative
assert negative["replay"]["gaps"] == 0, negative
assert negative["trust"]["trusted_assumptions"] == [], negative
assert any(finding["kind"] == "ensure-unproven" and finding["name"] == "caller_cannot_bound_opaque_call"
           for finding in negative["findings"]), negative

print("pure call-result bounds replay; opaque call-result bound remains unproved")
