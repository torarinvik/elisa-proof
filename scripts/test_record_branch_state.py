"""Conditional record post-states replay; stale/aliased/opaque states stay rejected."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, positive = run("record_branch_state_probe.elisa")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert all(d["verified"] for d in positive["declaration_details"] if d["kind"] == "function")
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0
assert positive["replay"]["gaps"] == 0 and not positive["trust"]["trusted_assumptions"]
code, negative = run("record_branch_state_rejected.elisa")
assert code == 1 and negative["status"] == "failed", negative
assert negative["summary"]["semantic_errors"] == 0, negative["summary"]
for name in ("record_branch_stale", "record_branch_wrong_arm", "record_branch_missing_arm",
             "record_branch_guard_rebound", "record_branch_alias", "record_branch_opaque_write"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven"
               for f in negative["findings"]), negative["findings"]
assert negative["replay"]["gaps"] == 0 and not negative["trust"]["trusted_assumptions"]
for fixture, name in (("record_branch_global_rejected.elisa", "record_branch_global"),
                      ("record_branch_deep_rejected.elisa", "record_branch_deep")):
    code, rejected = run(fixture)
    assert code == 1 and rejected["status"] == "failed", rejected
    assert rejected["summary"]["semantic_errors"] == 0, rejected["summary"]
    assert any(f["name"] == name and f["kind"] == "ensure-unproven"
               for f in rejected["findings"]), rejected["findings"]
    assert rejected["replay"]["gaps"] == 0 and not rejected["trust"]["trusted_assumptions"]
code, old_resource = run("contract_old_resource_rejected.elisa")
assert code == 1 and old_resource["status"] == "failed", old_resource
assert any(f["name"] == "contract_old_nested_effect" and f["kind"] in
           ("borrow-call-opaque", "contract-proposition-type", "contract-call-unsupported")
           for f in old_resource["findings"]), old_resource["findings"]
assert any(f["name"] == "contract_old_address" and f["kind"] == "borrow-contract-unsupported"
           for f in old_resource["findings"]), old_resource["findings"]
print("conditional record states replay; stale, wrong-arm, missing, rebound, aliased and opaque states rejected")
