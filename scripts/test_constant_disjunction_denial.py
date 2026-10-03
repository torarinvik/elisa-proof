"""Closed constant alternatives eliminate without admitting true/symbolic ones."""
import collections
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
p = subprocess.run([binary, "--json", str(ROOT / "test/constant_disjunction_denial.elisa")],
                   capture_output=True, text=True, timeout=60)
r = json.loads(p.stdout)
assert p.returncode == 1 and r["summary"]["semantic_errors"] == 0
assert not r["trust"]["trusted_assumptions"]
assert r["replay"] == {"certificates": 7, "replayed": 7, "gaps": 0}
for name in ("closed_order_denial", "reversed_order_denial"):
    goals = [g for g in r["goals"] if g["name"] == name]
    assert goals and all(g["proven"] and g["replay_status"] == "replayed" for g in goals)
negatives = ("rejected_true_order", "rejected_symbolic_order", "rejected_wrong_value")
for name in negatives:
    assert any(not g["proven"] for g in r["goals"] if g["name"] == name)
assert collections.Counter((f["name"], f["kind"]) for f in r["findings"]) == {
    (name, "ensure-unproven"): 1 for name in negatives
}
print("constant disjunctions: closed positives replay; true, symbolic and wrong-value controls reject")
