"""Guarded primitive index predicates support bounded Boolean denial, not false goals."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(fixture, status):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / fixture)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == status, (fixture, run.returncode, run.stderr)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data["summary"]
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
    assert data["trust"]["trusted_assumptions"] == [], data["trust"]
    return data


for fixture, count in (("disjunctive_goals.elisa", 13), ("leaving_branch_join.elisa", 24)):
    data = report(fixture, 0)
    assert data["status"] == "proved" and data["findings"] == [], data["findings"]
    assert data["summary"]["obligations"] == data["summary"]["proven"] == count, data["summary"]
    assert all(g["proven"] and g["replay_status"] == "replayed" for g in data["goals"])

data = report("rejected_disjunctive_goals.elisa", 1)
assert {(f["name"], f["kind"]) for f in data["findings"]} == {
    ("rejected_either", "ensure-unproven"), ("rejected_bound", "ensure-unproven"),
    ("rejected_wrong_side", "ensure-unproven"),
}, data["findings"]
data = report("rejected_leaving_branch_join.elisa", 1)
assert {(f["name"], f["kind"]) for f in data["findings"]} == {
    ("inverted_guard", "index-upper-unproven"), ("falling_branch_call", "ensure-unproven"),
    ("condition_call", "ensure-unproven"), ("scrutinee_call", "ensure-unproven"),
    ("match_falling_arm_call", "ensure-unproven"),
}, data["findings"]
print("indexed Boolean denial: guarded reads and leaving joins replay; false controls refused")
