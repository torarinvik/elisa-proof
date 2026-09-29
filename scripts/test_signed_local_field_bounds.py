"""A signed local or struct field narrower than 64 bits carries both ends of its type range,
so `x / 2 <= 16383` closes for an i16 local or field. A bound one inside the range, a narrow
field held to a tighter bound, and a reassigned local's value stay unproven."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/signed_local_field_bounds.elisa")
assert data["summary"]["proven"] == 15 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 15

data = run(ROOT / "examples/rejected_signed_local_field_bounds.elisa")
assert data["replay"]["gaps"] == 0
assert sorted((f["name"], f["line"], f["kind"]) for f in data["findings"]) == [
    ("field_too_tight", 14, "ensure-unproven"), ("local_too_tight", 10, "ensure-unproven"),
    ("narrow_field_wide", 18, "ensure-unproven"), ("reassigned", 24, "ensure-unproven")], data["findings"]

print("signed local and field bounds: both ends of the type range; tighter bounds refused")
