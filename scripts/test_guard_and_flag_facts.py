"""Nested guard clauses (`continue if`, `return ... if` inside a loop or a branch) and a bool
local that names a comparison (`ok: bool = i < n; if ok:`) both carry their fact. A reassigned
flag, a moved operand, and the negated branch stay unproven."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/guard_and_flag_facts.elisa")
assert data["summary"]["proven"] == 9 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 9

data = run(ROOT / "examples/rejected_guard_and_flag_facts.elisa")
assert data["replay"]["gaps"] == 0
assert sorted((f["name"], f["line"], f["kind"]) for f in data["findings"]) == [
    ("moved_index", 15, "ensure-unproven"), ("negated_flag", 22, "ensure-unproven"),
    ("reassigned_flag", 6, "ensure-unproven")], data["findings"]

print("guard and flag facts: nested guards and bool locals carry facts; stale flags refused")
