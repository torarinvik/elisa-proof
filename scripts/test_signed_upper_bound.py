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
assert data["summary"]["proven"] == 6 and data["summary"]["failed"] == 0 and data["findings"] == []
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 6

data = run("rejected_signed_lower_bound.elisa")
assert data["summary"]["failed"] == 3 and data["replay"]["gaps"] == 0
assert [(f["name"], f["line"]) for f in data["findings"]] == [("narrow_floor", 3), ("beyond_floor", 7), ("unsigned_floor", 11)], data["findings"]
# `-(MAX+1)` is the only negated literal past the maximum with one typed value; one further, or any
# negative literal at an unsigned width, stays out of width.
gates = {g["name"]: g.get("refusal_gate") for g in data["goals"] if not g["proven"]}
assert gates == {"narrow_floor": "no-rule", "beyond_floor": "literal-width", "unsigned_floor": "literal-width"}, gates

print("signed upper bound: i8 parameter proves <= 127 and refuses <= 126; >= -128 proves and >= -129 is out of width")
