"""Literal negation elimination cannot grant truth to live/symbolic alternatives."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
run = subprocess.run([BIN, "--json", str(ROOT / "test/literal_negation_disjunction_probe.elisa")],
                     capture_output=True, text=True, timeout=60)
r = json.loads(run.stdout)
assert run.returncode == 1 and r["summary"]["semantic_errors"] == 0
assert r["replay"]["certificates"] == r["replay"]["replayed"] and r["replay"]["gaps"] == 0
assert not r["trust"]["trusted_assumptions"]
for name, expected in (("direct_literal_denial", True), ("nested_literal_denials", True),
                       ("parenthesized_literal_denial", True), ("repeated_literal_negation", True),
                       ("selector", True), ("checked_call_literal_denial", True),
                       ("rejected_true_alternative", False), ("rejected_symbolic_alternative", False),
                       ("rejected_wrong_literal_value", False), ("rejected_wrong_checked_result", False)):
    goals = [g for g in r["goals"] if g["name"] == name and g["rule"] == "goal"]
    assert goals and all(g["proven"] == expected for g in goals), name
print("literal-not false alternatives replay; true/symbolic alternatives and wrong values reject")
