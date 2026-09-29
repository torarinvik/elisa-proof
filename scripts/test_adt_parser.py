"""The named-tuple parser proves and replays in full: each ensure reads a label of the result,
projected by position from the returned tuple, and a label of a pure call's result is one typed
value. Each broken counterpart is refused, and replay withholds the only unproven function's own
summary from its proofs."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=120)
    return result.returncode, json.loads(result.stdout)


code, data = run("adt_parser.elisa")
assert code == 0 and data["status"] == "proved", (code, data["findings"])
assert data["findings"] == [] and data["summary"]["semantic_errors"] == 0, data["findings"]
assert data["replay"]["gaps"] == 0, data["replay"]
assert data["replay"]["certificates"] == data["replay"]["replayed"] >= 35, data["replay"]

code, data = run("rejected_adt_parser.elisa")
assert code == 1 and data["status"] == "failed", code
assert data["summary"]["semantic_errors"] == 0, data["semantic_diagnostics"]
findings = sorted({(f["kind"], f["line"], f["name"]) for f in data["findings"]})
assert findings == [
    ("ensure-unproven", 16, "consumes_nothing"),
    ("ensure-unproven", 23, "swapped_labels"),
    ("ensure-unproven", 36, "sum_reads_nothing"),
    ("ensure-unproven", 64, "length_below_ten"),
    ("ensure-unproven", 70, "value_is_a_byte"),
    ("ensure-unproven", 75, "repeated_label"),
], findings
gaps = {g["name"] for g in data["goals"] if g["replay_status"] == "gap"}
assert gaps == {"sum_reads_nothing"}, gaps

print("adt parser: named-tuple results proved by structural induction, replayed; broken variants refused")
