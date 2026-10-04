"""Checked loop post-state survives capture syntax; invalid exits remain rejected."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")

def run(fixture):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert r["summary"]["semantic_errors"] == 0
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    return p.returncode, r

for fixture in ("open_history_length_prefix.elisa", "quantified_prefix_exit.elisa", "captured_block.elisa", "block_statement_region.elisa"):
    code, r = run(fixture)
    assert code == 0 and r["status"] == "proved", (fixture, r["findings"])
    assert r["summary"]["proven"] == r["summary"]["obligations"] > 0
code, r = run("rejected_loop_entry_state.elisa")
assert code == 1 and r["status"] == "failed"
for name, kind in (("entry_value_must_not_reach_the_body", "call-requires-unproven"),
                   ("entry_value_must_not_reach_an_uncaptured_body", "call-requires-unproven"),
                   ("false_invariant_must_not_be_preserved", "invariant-not-preserved"),
                   ("break_must_not_yield_the_exit_condition", "ensure-unproven")):
    assert any(f["name"] == name and f["kind"] == kind for f in r["findings"]), r["findings"]
    assert not any(d.get("name") == name and d.get("verified") for d in r["declaration_details"])
for fixture in ("rejected_captured_block.elisa", "rejected_uncaptured_block_write.elisa",
                "rejected_block_statement_region.elisa", "rejected_loop_break.elisa"):
    code, r = run(fixture)
    assert code == 1 and r["status"] == "failed" and r["findings"], (fixture, r)
print("captured loop exit and complete length-prefix loop replay; false entry, invariant, break-exit and opaque-block controls reject")
