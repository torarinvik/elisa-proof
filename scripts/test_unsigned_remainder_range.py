"""Unsigned remainder safety uses a positive divisor's modular range only."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/unsigned_remainder_range.elisa")],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr)
data = json.loads(run.stdout)
assert data["summary"]["semantic_errors"] == data["summary"]["semantic_diagnostics"] == 0, data
assert data["replay"]["gaps"] == 0, data
assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data
functions = {d["name"]: d for d in data["declaration_details"] if d.get("kind") == "function"}
for name in ("remainder_below_positive_divisor", "conditional_rounded_quotient",
             "quotient_successor_lower_bound", "quotient_successor_upper_bound"):
    assert functions[name]["verified"], (name, functions[name])
    assert not any(g["name"] == name and not g["proven"] for g in data["goals"]), name
negative = functions["untrue_tighter_remainder_bound"]
assert not negative["verified"], negative
assert any(g["name"] == "untrue_tighter_remainder_bound" and not g["proven"] for g in data["goals"]), data
for name in ("wrapping_successor_control",):
    assert not functions[name]["verified"], functions[name]
    assert any(g["name"] == name and not g["proven"] for g in data["goals"]), data
print("unsigned remainder/successor: bounded claims replay; tighter and wrapping controls stay open")
