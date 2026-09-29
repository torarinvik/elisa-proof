"""Twelve chained calls to one contracted pure function prove and replay quickly. Replay once
revalidated every summary's precondition certificates per call path, which grew about 4x per call;
the timeout here is the regression bound."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))

result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/chained_pure_calls.elisa")],
                        capture_output=True, text=True, timeout=60)
data = json.loads(result.stdout)
assert result.returncode == 0 and data["status"] == "proved", data["findings"]
assert data["replay"]["gaps"] == 0, data["replay"]
assert data["replay"]["certificates"] == data["replay"]["replayed"] >= 30, data["replay"]
assert data["measurements"]["kernel_nodes"] < 2000, data["measurements"]

print("chained pure calls: replay stays linear in the chain length")
