"""`v.pop()` on a mutable darray reference parameter shrinks `v.count` by exactly one, implies the
count was at least one, and keeps element facts that avoid the popped slot (BACKLOG W-04). The
rejected fixtures pin that an overstated count, the popped slot, a conditional pop, a pop of
another collection, a pop then push, a value-position pop, a pop with an argument and a user
function named `pop` all leave the claim unproven; a run of 40 pops stays one sum deep."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/collection_pop.elisa")
assert data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["replay"]["gaps"] == 0 and data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]

data = run(ROOT / "examples/rejected_collection_pop.elisa")
assert data["status"] == "failed" and data["replay"]["gaps"] == 0
failures = sorted((finding["kind"], finding["line"]) for finding in data["findings"])
assert failures == [("ensure-unproven", line) for line in (2, 6, 11, 16, 20, 26, 31)], failures

data = run(ROOT / "examples/rejected_collection_pop_user_method.elisa")
assert data["status"] == "failed" and data["replay"]["gaps"] == 0
goals = [goal for goal in data["goals"] if goal["name"] == "shadowed" and goal["rule"] == "goal"]
assert goals and not any(goal["proven"] for goal in goals), goals

print("collection pop: a builtin pop removes exactly one element and keeps the rest")
