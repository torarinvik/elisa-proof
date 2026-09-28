"""A numeric cast is a witnessed scalar term, never an identity on its receiver."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/rejected_numeric_cast_operator.elisa"
run = subprocess.run([str(BINARY), "--json", str(SOURCE)],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr, run.stdout)
data = json.loads(run.stdout)
assert data["status"] == "failed", data
assert data["summary"]["semantic_errors"] == 0, data
assert data["replay"]["gaps"] == 0, data
found = sorted((f["line"], f["name"], f["kind"]) for f in data["findings"])
assert found == [
    (9, "wrapped_cast_below", "ensure-unproven"),
    (15, "truncated_cast_above", "ensure-unproven"),
    (21, "truncated_cast_positive", "ensure-unproven"),
], found
assert not any(goal["proven"] for goal in data["goals"] if goal["rule"] == "goal"), data["goals"]

print("numeric casts: a cast's value is not read through its receiver")
