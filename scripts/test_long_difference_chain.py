"""The interval pass over difference constraints runs to a fixed point (BACKLOG C-01): a bound
stated at the far end of a chain reaches its first name however many links apart, in the producer
and the kernel alike. The rejected fixture pins that it invents no bound, and that a contradictory
cycle, which would tighten forever, stops at the limit."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


started = time.monotonic()
data = run(ROOT / "examples/long_difference_chain.elisa")
elapsed = time.monotonic() - started
assert data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["summary"]["proven"] == 10 and data["replay"] == {"certificates": 10, "replayed": 10, "gaps": 0}, data["replay"]
# Budget: the thirty-two-name chain is the widest the limit is sized for and stays cheap.
assert elapsed < 60, elapsed

data = run(ROOT / "examples/rejected_long_difference_chain.elisa")
assert data["status"] == "failed" and data["replay"]["gaps"] == 0
assert data["replay"]["certificates"] == data["replay"]["replayed"]
failures = sorted((finding["kind"], finding["line"]) for finding in data["findings"])
assert failures == [("ensure-unproven", 9), ("ensure-unproven", 22), ("ensure-unproven", 34), ("ensure-unproven", 42)], failures

print("long difference chain: bounds travel every link, and only the ones the facts imply")
