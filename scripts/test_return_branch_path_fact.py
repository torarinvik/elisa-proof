"""Early-return branch facts replay independently for scalar-reference writes."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/return_branch_path_fact.elisa")],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr)
data = json.loads(run.stdout)
assert data["summary"]["semantic_errors"] == 0, data
assert data["replay"]["gaps"] == 0, data
assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data
functions = {d["name"]: d for d in data["declaration_details"] if d.get("kind") == "function"}
for name in ("else_path_le", "scalar_store", "subtraction_path_bound", "subtraction_path_bound_u64"):
    assert functions[name]["verified"], (name, functions[name])
    assert not any(g["name"] == name and not g["proven"] for g in data["goals"]), name
negative = functions["else_path_negative_control"]
assert not negative["verified"], negative
assert any(f["name"] == "else_path_negative_control" and f["kind"] == "ensure-unproven"
           and f["status"] == "disproved" and f["counterexample_found"] for f in data["findings"]), data
strict_negative = functions["subtraction_path_strict_negative"]
assert not strict_negative["verified"], strict_negative
assert any(f["name"] == "subtraction_path_strict_negative" and f["kind"] == "ensure-unproven"
           and f["status"] in ("disproved", "unknown") for f in data["findings"]), data
float_negative = functions["floating_nan_negative_control"]
assert not float_negative["verified"], float_negative
assert any(f["name"] == "floating_nan_negative_control"
           and f["kind"] in ("ensure-unproven", "contract-expression-unsupported")
           and f["status"] in ("disproved", "unknown", "unsupported") for f in data["findings"]), data
print("return branch facts: scalar updates and u64 bounds replay; strict and floating claims are conservatively refused")
