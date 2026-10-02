"""An unsigned increment under a strict peer (`i < n` or `i < values.count`) does not wrap, so
`i + 1 > i` closes for usize and u64. A non-strict or missing peer, and a result held below the
count, stay unproven."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/usize_increment_under_count.elisa")
assert data["summary"]["proven"] == data["summary"]["obligations"] == 11 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 11

data = run(ROOT / "examples/rejected_usize_increment_under_count.elisa")
assert data["replay"]["gaps"] == 0
assert sorted((f["name"], f["line"], f["kind"]) for f in data["findings"]) == [
    ("non_strict", 4, "ensure-unproven"), ("overshoot", 13, "ensure-unproven"),
    ("unguarded", 8, "ensure-unproven")], data["findings"]

print("usize increment under count: strict peers bound the increment; others refused")
