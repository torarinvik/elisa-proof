"""A subtraction witness proves a safe unsigned sum upper bound; no witness does not."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/unsigned_sum_upper_shape.elisa")],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr)
data = json.loads(run.stdout)
assert data["summary"]["semantic_errors"] == 0, data
assert data["replay"]["gaps"] == 0, data
assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data
functions = {d["name"]: d for d in data["declaration_details"] if d.get("kind") == "function"}
assert functions["bounded_unsigned_sum"]["verified"], functions["bounded_unsigned_sum"]
assert not functions["unbounded_unsigned_sum_control"]["verified"], functions["unbounded_unsigned_sum_control"]
assert any(g["name"] == "unbounded_unsigned_sum_control" and not g["proven"] for g in data["goals"]), data
print("unsigned sum upper bound: witness replays; unbounded control remains open")
