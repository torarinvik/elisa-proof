"""A `can` effect block keeps the facts its body leaves alone (BACKLOG D-01, inferred frame):
its writes and calls havoc what they reach inside the block, and facts over its locals leave
with its scope. The rejected fixture pins that a mutably passed collection, an assigned local
and a block-local relation are all forgotten."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/can_block_frame.elisa")
assert data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["replay"]["gaps"] == 0 and data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]

data = run(ROOT / "examples/rejected_can_block_frame.elisa")
assert data["status"] == "failed" and data["replay"]["gaps"] == 0
failures = sorted((finding["kind"], finding["line"]) for finding in data["findings"])
assert failures == [("ensure-unproven", 18), ("ensure-unproven", 27), ("index-upper-unproven", 9)], failures

print("can block frame: effect blocks keep untouched facts and only those")
