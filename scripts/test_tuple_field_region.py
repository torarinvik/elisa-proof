"""A named-tuple call result over a region handle, bound to a local, keeps each scalar label's
declared type, so the callee's label summaries prove goals after the binding. The witness is a
type, never a bound: goals needing more than the callee ensures still fail. Many bound tuples in
one body stay within the fact budget."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/tuple_field_region.elisa")
assert data["summary"]["proven"] == 9 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 9

data = run(ROOT / "examples/rejected_tuple_field_region.elisa")
assert data["summary"]["failed"] == 5 and data["replay"]["gaps"] == 0
assert [(f["name"], f["line"]) for f in data["findings"]] == [
    ("unbounded_count", 19), ("small_overflow", 24), ("other_label", 29),
    ("wrong_label", 34), ("reordered_label", 39)], data["findings"]

with tempfile.TemporaryDirectory() as directory:
    # Malformed: a label that the callee does not declare adds no witness and proves nothing.
    path = Path(directory) / "missing_label.elisa"
    path.write_text("def pick[@r](value: JsonValueHandle[r]) -> (count: i64, value: JsonValueHandle[r]):\n"
                    "    ensure result.count >= 0\n    return (1, value)\n\n"
                    "def use[@r](value: JsonValueHandle[r]) -> i64:\n    ensure result >= 1\n"
                    "    found: (total: i64, value: JsonValueHandle[r]) = pick(value)\n    return found.total + 1\n")
    data = run(path)
    assert data["summary"]["failed"] >= 1 and data["replay"]["gaps"] == 0, data["summary"]
    # Budget: 30 bound tuples in one body.
    lines = ["def pick[@r](value: JsonValueHandle[r]) -> (count: u8, value: JsonValueHandle[r]):",
             "    ensure result.count <= 5", "    return (1, value)", "",
             "def many[@r](value: JsonValueHandle[r]) -> u8:", "    ensure result <= 10"]
    lines += [f"    f{i}: (count: u8, value: JsonValueHandle[r]) = pick(value)" for i in range(30)]
    lines += ["    return f29.count + f0.count"]
    path = Path(directory) / "many.elisa"
    path.write_text("\n".join(lines) + "\n")
    data = run(path)
    assert data["replay"]["gaps"] == 0, data["summary"]
    assert {f["kind"] for f in data["findings"]} <= {"control-flow-analysis-budget", "ensure-unproven"}, data["findings"]

print("tuple field region: ordered field summaries replay; wrong and reordered labels are refused")
