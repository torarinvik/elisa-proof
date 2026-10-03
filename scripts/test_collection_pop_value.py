"""`x: T = v.pop()` on the builtin darray pop binds the last element and shrinks the count by one
(BACKLOG W-04, value position). The rejected fixtures pin that a value the facts do not give,
the first element read as the last, the popped slot past the new count, and an unchanged count
all stay unproven."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/collection_pop_value.elisa")
assert data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["replay"]["gaps"] == 0 and data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]

data = run(ROOT / "examples/rejected_collection_pop_value.elisa")
assert data["status"] == "failed" and data["replay"]["gaps"] == 0
failures = sorted((finding["kind"], finding["line"]) for finding in data["findings"])
assert failures == [("ensure-unproven", line) for line in (5, 11, 17, 22, 29)], failures

print("collection pop value: a value pop binds the last element and removes it")
