"""`v.push(x)` on a mutable darray reference parameter grows `v.count` by exactly one, and
`old(v.count)` names the count at entry (BACKLOG D-02). The rejected fixtures pin that a
missing, undone, conditional or unrecognised push, a push to another collection, and a user
function named `push` all leave the count claim unproven."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/collection_push_count.elisa")
assert data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["replay"]["gaps"] == 0 and data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]

data = run(ROOT / "examples/rejected_collection_push_count.elisa")
assert data["status"] == "failed" and data["replay"]["gaps"] == 0
failures = sorted((finding["kind"], finding["line"]) for finding in data["findings"])
assert failures == [("ensure-unproven", line) for line in (5, 9, 14, 19, 23)], failures

data = run(ROOT / "examples/rejected_collection_push_user_method.elisa")
assert data["status"] == "failed" and data["replay"]["gaps"] == 0
goals = [goal for goal in data["goals"] if goal["name"] == "shadowed" and goal["rule"] == "goal"]
assert goals and not any(goal["proven"] for goal in goals), goals

print("collection push count: a builtin push adds one element and old(v.count) is the entry count")
