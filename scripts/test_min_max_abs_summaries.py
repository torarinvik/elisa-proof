"""Elisa has no min/max/abs builtins, so user functions written as conditionals carry them. A
disjunctive ensure `result == a or result == b` over a conditional result is split on the
conditional across the whole disjunction, in the producer and the replay kernel, and a caller
(`clamp`) uses the summaries. Off-by-one and wrong-side ensures stay unproven."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/min_max_abs_summaries.elisa")
assert data["summary"]["proven"] == 19 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 19

data = run(ROOT / "examples/rejected_min_max_abs_summaries.elisa")
assert data["replay"]["gaps"] == 0
assert sorted((f["name"], f["line"], f["kind"]) for f in data["findings"]) == [
    ("abs_off_by_one", 17, "ensure-unproven"), ("max_one_side", 7, "ensure-unproven"),
    ("min_of_min", 22, "ensure-unproven"), ("min_shifted", 12, "ensure-unproven"),
    ("min_strict", 3, "ensure-unproven")], data["findings"]

print("min/max/abs summaries: disjunctive ensures split on the conditional; off-by-one refused")
