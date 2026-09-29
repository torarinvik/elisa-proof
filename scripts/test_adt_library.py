"""The ADT proof library proves and replays in full; each of its broken counterparts is refused,
and replay withholds a function's own summary from its proofs while that function has an
unproven goal."""
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


code, data = run("adt_library.elisa")
assert code == 0 and data["status"] == "proved", (code, data["findings"])
assert data["findings"] == [] and data["summary"]["semantic_errors"] == 0, data["findings"]
assert data["replay"]["gaps"] == 0, data["replay"]
assert data["replay"]["certificates"] == data["replay"]["replayed"] >= 70, data["replay"]

code, data = run("rejected_adt_library.elisa")
assert code == 1 and data["status"] == "failed", code
findings = sorted({(f["kind"], f["line"], f["name"]) for f in data["findings"]})
assert findings == [
    ("ensure-unproven", 25, "count_is_zero"),
    ("ensure-unproven", 35, "spin"),
    ("ensure-unproven", 45, "tree_spin"),
    ("ensure-unproven", 54, "wrong_constructor"),
    ("ensure-unproven", 68, "shallow"),
    ("ensure-unproven", 81, "max_below_floor"),
    ("ensure-unproven", 94, "length_below_cap"),
    ("structural-decreases-unproven", 35, "spin"),
    ("structural-decreases-unproven", 45, "tree_spin"),
], findings
# The compiler's own structural check refuses the two non-descending recursions as well.
semantic = sorted((d["line"], d["name"]) for d in data["semantic_diagnostics"] if d["severity"] == 1)
assert semantic == [(28, "spin"), (38, "tree_spin")], semantic
# Every replay gap is a goal the checker closed with the function's own unverified summary.
failing = {name for (_, _, name) in findings}
gaps = [(g["line"], g["name"]) for g in data["goals"] if g["replay_status"] == "gap"]
assert gaps and all(name in failing for (_, name) in gaps), gaps
assert {name for (_, name) in gaps} == {"shallow", "max_below_floor", "length_below_cap"}, gaps

print("adt library: lists, trees and token streams proved by structural induction, replayed; broken variants refused")
