"""Signed named-tuple call results carry their declared element ranges into local bindings."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run("signed_tuple_label_bounds.elisa")
assert data["summary"]["proven"] == data["summary"]["obligations"], data["summary"]
assert data["replay"]["gaps"] == 0
assert data["replay"]["replayed"] == data["replay"]["certificates"]

data = run("rejected_signed_tuple_label_bounds.elisa")
assert data["replay"]["gaps"] == 0 and data["summary"]["unproven"] == 2
assert sorted((finding["name"], finding["kind"]) for finding in data["findings"]) == [
    ("tuple_half_too_high", "ensure-unproven"),
    ("tuple_half_too_low", "ensure-unproven"),
], data["findings"]

print("signed tuple labels: both declared-width bounds replay; tighter claims refused")
