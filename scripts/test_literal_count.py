"""A collection literal of up to eight elements has its length as a constant, read by comparison
in the producer and the replay kernel, so a literal table's count and a walk over it prove.
The boundary (a nine-element literal, a wrong length) lives in rejected_literal_extent."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/literal_count.elisa")
assert data["summary"]["proven"] == 11 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 11

print("literal count: short literals carry their length")
