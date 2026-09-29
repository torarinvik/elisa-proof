"""A call to a verified callee whose only departure from purity is a precondition keeps its
summary across a later call. Callees with effects, a mutable global read, a mutable borrow
argument, or a call to such a callee keep nothing. A long chain stays within the witness budget."""
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


data = run(ROOT / "examples/deterministic_call_chain.elisa")
assert data["summary"]["proven"] == 16 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 16

data = run(ROOT / "examples/rejected_deterministic_call_chain.elisa")
assert data["summary"]["failed"] == 4 and data["replay"]["gaps"] == 0
assert [(f["name"], f["line"]) for f in data["findings"]] == [
    ("effect_chain", 17), ("global_chain", 30), ("borrow_chain", 44), ("indirect_chain", 57)], data["findings"]

# Budget: 40 chained calls in one body. Retained summaries grow the fact snapshots until the
# control-flow budget refuses the rest of the body; that refusal is the only failure, and
# everything proved before it still replays.
lines = ["def step(x: i64) -> i64:", "    requires x >= 0", "    ensure result >= 0",
         "    ensure result <= 10", "    return x if x <= 10 else 10", "",
         "def long_chain(x: i64) -> i64:", "    requires x >= 0", "    ensure result >= 0",
         "    v0: i64 = step(x)"]
lines += [f"    v{i}: i64 = step(v{i - 1})" for i in range(1, 40)]
lines += ["    return v39"]
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "long_chain.elisa"
    path.write_text("\n".join(lines) + "\n")
    data = run(path)
assert data["replay"]["gaps"] == 0 and data["summary"]["proven"] > 0, data["summary"]
assert {f["kind"] for f in data["findings"]} <= {"control-flow-analysis-budget"}, data["findings"]

print("deterministic call chain: precondition-only callees keep summaries; effects, globals, borrows refused")

# BACKLOG B-04: the "c4 scalar witness" probe, a kept summary beside a widened u8 argument.
data = run(ROOT / "examples/widened_call_result.elisa")
assert data["summary"]["failed"] == 0 and data["replay"]["gaps"] == 0 and data["summary"]["proven"] == 9, data["summary"]
data = run(ROOT / "examples/rejected_widened_call_result.elisa")
assert [(f["name"], f["line"]) for f in data["findings"]] == [("too_tight", 14)] and data["replay"]["gaps"] == 0, data["findings"]
print("widened call result: the c4 probe proves, and its bound is tight")
