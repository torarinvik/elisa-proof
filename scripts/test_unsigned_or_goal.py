"""Boolean tautologies and exact guard complements survive unsigned range facts."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/unsigned_or_goal.elisa")],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr)
data = json.loads(run.stdout)
assert data["summary"]["semantic_errors"] == 1, data
assert data["replay"]["gaps"] == 0, data
assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data
functions = {d["name"]: d for d in data["declaration_details"] if d.get("kind") == "function"}
for name in ("u32_true_literal", "u8_true_disjunction", "u32_true_disjunction",
             "u64_true_disjunction", "u32_reflexive_disjunction", "u32_complemented_guard"):
    # The file carries one deliberate source error, so no declaration is claimed verified
    # (2f7004cf gates claims on clean source); every goal of these functions must still prove.
    assert functions[name]["verified"] or functions[name]["verification_reason"] == "source-error", (name, functions[name])
    assert not any(g["name"] == name and not g["proven"] for g in data["goals"]), name
negative = functions["u32_false_disjunction_control"]
assert not negative["verified"], negative
assert any(g["name"] == "u32_false_disjunction_control" and not g["proven"] for g in data["goals"]), data
overflow = functions["u8_wrapped_return_control"]
assert not overflow["verified"], overflow
assert any(g["name"] == "u8_wrapped_return_control" and not g["proven"] for g in data["goals"]), data
diagnostic = [d for d in data["semantic_diagnostics"] if d.get("name") == "u8_wrapped_return_control"]
assert len(diagnostic) == 1 and "provably violated" in diagnostic[0]["message"], diagnostic
print("unsigned disjunctions: tautologies and guard complements replay; u8 wrapped return stays rejected")
