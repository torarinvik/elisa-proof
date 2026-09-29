"""A signed parameter narrower than 64 bits is bounded above by its type (`v: i8` gives
`v <= 127`). The front end cannot show such a postcondition statically, so its own diagnostic is
expected; the proof engine's obligations are what this test reads. The lower bound is imported too, spelled `-MAX - 1`."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


data = run("signed_upper_bound.elisa")
assert data["summary"]["proven"] == 2 and data["summary"]["failed"] == 0 and data["findings"] == []
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 2

data = run("rejected_signed_upper_bound.elisa")
assert data["summary"]["failed"] == 1 and data["replay"]["gaps"] == 0
assert [(f["name"], f["line"]) for f in data["findings"]] == [("narrow", 3)], data["findings"]

data = run("signed_lower_bound.elisa")
assert data["summary"]["proven"] == 4 and data["summary"]["failed"] == 0 and data["findings"] == []
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 4

data = run("rejected_signed_lower_bound.elisa")
assert data["summary"]["failed"] == 1 and data["replay"]["gaps"] == 0
assert [(f["name"], f["line"]) for f in data["findings"]] == [("narrow_floor", 3)], data["findings"]

print("signed upper bound: i8 parameter proves <= 127 and refuses <= 126")
