"""Scalar reference indexing is typed through the single valid subscript only."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/scalar_reference_index.elisa")],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr)
data = json.loads(run.stdout)
assert data["summary"]["semantic_errors"] == 0, data
assert data["replay"]["gaps"] == 0, data
assert data["replay"]["certificates"] == data["replay"]["replayed"], data
for name in ("reference_read", "reference_update", "reference_byte_cast", "reference_disjunctive_update",
             "reference_observe_entry", "reference_observe_through_call"):
    assert not any(f["name"] == name and f["kind"] in
                   ("expression-unsupported", "contract-proposition-type", "index-bounds-opaque")
                   for f in data["findings"]), data
    assert any(d.get("name") == name and d.get("verified") for d in data["declaration_details"]), name
through_call = {d["name"]: d for d in data["declaration_details"] if d.get("kind") == "function"}
assert not through_call["reference_update_through_call"]["verified"], through_call
assert any(f["name"] == "reference_update_through_call" and f["kind"] == "call-old-opaque"
           for f in data["findings"]), data
assert not any(d["name"] == "reference_observe_false" and d.get("verified")
               for d in data["declaration_details"]), data
assert any(f["name"] == "reference_observe_false" and f["kind"] == "ensure-unproven"
           for f in data["findings"]), data
assert not any(d["name"] == "reference_observe_after_impure_call" and d.get("verified")
               for d in data["declaration_details"]), data
assert any(f["name"] == "reference_observe_after_impure_call" and f["kind"] == "call-old-opaque"
           for f in data["findings"]), data
assert any(t["kind"] == "function-summary" and t["dependency"] == "reference_observe_entry" and
           len(t["summary_bindings"]) == 3 and t["summary_bindings"][-1]["parameter"] == "__old_reference_state"
           for t in data["kernel"]["fact_traces"]), data
assert any(f["name"] == "rejected_reference_offset" and
           f["kind"] == "contract-proposition-type" for f in data["findings"]), data
assert not any(g["name"] == "rejected_reference_offset" and g["rule"] == "goal" and g["proven"]
               for g in data["goals"]), data
print("scalar reference indexing: direct reads/updates and pure call-entry snapshots replayed; mutating old-call and nonzero offset safely refused")
