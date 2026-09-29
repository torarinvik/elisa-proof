"""`name is Enum.Variant` in a goal is one builtin bool, so `result == (c is E.V)` closes by
equality. A different variant or subject stays unproven, a call subject is refused as a
proposition, and a wide conjunction of tag tests stays within the fact budget."""
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


data = run(ROOT / "examples/enum_tag_equality.elisa")
assert data["summary"]["proven"] == 4 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 4

data = run(ROOT / "examples/rejected_enum_tag_equality.elisa")
assert data["replay"]["gaps"] == 0
assert sorted((f["name"], f["line"], f["kind"]) for f in data["findings"]) == [
    ("call_subject", 18, "contract-proposition-type"), ("swapped_subject", 15, "ensure-unproven"),
    ("wrong_variant", 11, "ensure-unproven")], data["findings"]

with tempfile.TemporaryDirectory() as directory:
    names = [f"c{i}" for i in range(24)]
    conjunction = " and ".join(f"({n} is Color.Red)" for n in names)
    path = Path(directory) / "wide.elisa"
    path.write_text("enum Color:\n    Red\n    Green\n\n"
                    f"def wide({', '.join(n + ': Color' for n in names)}) -> bool:\n"
                    f"    ensure result == ({conjunction})\n    return {conjunction}\n")
    data = run(path)
    assert data["replay"]["gaps"] == 0, data["summary"]
    assert {f["kind"] for f in data["findings"]} <= {"ensure-unproven", "control-flow-analysis-budget"}, data["findings"]

print("enum tag equality: named tag tests are bools; other variants, subjects and calls refused")
