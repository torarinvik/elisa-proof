"""Forced alternatives replay without consuming the case-split budget."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O: assertions must remain enabled")

def run(name):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / name)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert r["summary"]["semantic_errors"] == 0
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    return p.returncode, r

code, positive = run("disjunctive_syllogism_probe.elisa")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["replay"]["replayed"] > 0
code, negative = run("disjunctive_syllogism_rejected.elisa")
assert code == 1 and negative["status"] == "failed"
for target in ("false_boolean_chain", "missing_chain_link", "unordered_float_alternative"):
    assert any(f["name"] == target and f["kind"] in
               ("ensure-unproven", "contract-proposition-type", "contract-expression-unsupported")
               for f in negative["findings"]), negative["findings"]
print("forced Boolean/integer alternatives replay; false, broken-chain and unordered-float controls reject")
