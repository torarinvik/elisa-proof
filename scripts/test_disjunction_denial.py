"""Bounded Boolean/equality denial replays without assuming floating order total."""
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


code, positive = run("disjunction_denial_probe.elisa")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0
assert positive["replay"]["gaps"] == 0 and not positive["trust"]["trusted_assumptions"]
code, negative = run("disjunction_denial_rejected.elisa")
assert code == 1 and negative["status"] == "failed", negative
assert negative["summary"]["semantic_errors"] == 0, negative["summary"]
for name in ("disjunction_denial_false_boolean", "disjunction_denial_false_nullable"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven"
               for f in negative["findings"]), negative["findings"]
assert any(f["name"] == "disjunction_denial_float_order" and f["kind"] in
           ("ensure-unproven", "contract-proposition-type")
           for f in negative["findings"]), negative["findings"]
assert negative["replay"]["gaps"] == 0 and not negative["trust"]["trusted_assumptions"]
print("bounded denial replays integer product order; false Boolean/null claims and total float order rejected")
