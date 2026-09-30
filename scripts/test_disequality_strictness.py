"""`a <= b` beside a fact `a != b` over the same two terms is `a < b`, in the producer and the
replay kernel, including a branch guard `if i != n`. A disequality over another term, one with
no order fact, and a two-step strengthening stay unproven."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/disequality_strictness.elisa")
assert data["summary"]["proven"] == 11 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 11

data = run(ROOT / "examples/rejected_disequality_strictness.elisa")
assert data["replay"]["gaps"] == 0
assert sorted((f["name"], f["line"], f["kind"]) for f in data["findings"]) == [
    ("disequality_alone", 10, "ensure-unproven"), ("other_pair", 5, "ensure-unproven"),
    ("two_steps", 16, "ensure-unproven")], data["findings"]

print("disequality strictness: <= and != give <; other pairs refused")
