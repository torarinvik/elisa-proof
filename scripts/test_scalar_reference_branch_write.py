#!/usr/bin/env python3
"""Branch joins retain frozen scalar-reference writes and refuse forged markers."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def inspect(source):
    run = subprocess.run([str(BINARY), "--json", str(source)],
                         capture_output=True, text=True, timeout=60)
    return run, json.loads(run.stdout)


run, report = inspect(ROOT / "examples/scalar_reference_branch_write.elisa")
assert run.returncode == 1, (run.returncode, run.stderr)
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
assert report["trust"]["trusted_assumptions"] == []
functions = {item["name"]: item for item in report["declaration_details"]
             if item.get("kind") == "function"}
for name in ("reference_branch_output_write", "reference_sequential_early_returns"):
    assert functions[name]["verified"], functions[name]
    assert not any(goal["name"] == name and not goal["proven"] for goal in report["goals"])
for name in ("reference_branch_output_write_false", "reference_sequential_early_returns_false"):
    assert not functions[name]["verified"], functions[name]
    assert any(finding["name"] == name and finding["kind"] == "ensure-unproven"
               and finding["status"] in ("disproved", "unknown")
               for finding in report["findings"]), name

run, forged = inspect(ROOT / "examples/rejected_forged_scalar_reference_state.elisa")
assert run.returncode == 1, (run.returncode, run.stderr)
assert forged["verification_state"] == "unsupported", forged
assert forged["replay"]["gaps"] == 0, forged["replay"]
assert forged["findings"] == [{
    "kind": "proof-internal-name", "status": "unsupported", "line": 2,
    "name": "__elisa_proof_scalar_reference_state",
    "message": "source identifier collides with a proof-system internal name",
    "counterexample_found": False, "goal_id": None, "counterexample": []
}], forged["findings"]
print("scalar reference branch writes: early-return state replays; false contracts and forged markers are refused")
