"""A later match arm knows that every earlier unguarded arm with an exact condition failed. The
positive file proves and replays in full. In the rejected file, each earlier arm could fail for a
reason its condition does not capture (a guard, a payload literal, a pin, or a call in an earlier
guard), so the refutation it would need is withheld."""
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


code, data = run("match_refuted_arms.elisa")
assert code == 0 and data["status"] == "proved", (code, data["findings"])
assert data["findings"] == [] and data["summary"]["semantic_errors"] == 0, data["findings"]
assert data["replay"]["gaps"] == 0, data["replay"]
assert data["replay"]["certificates"] == data["replay"]["replayed"] >= 27, data["replay"]

code, data = run("rejected_match_refuted_arms.elisa")
assert code == 1 and data["status"] == "failed", code
assert data["summary"]["semantic_errors"] == 0, data["semantic_diagnostics"]
findings = sorted({(f["kind"], f["line"], f["name"]) for f in data["findings"]})
assert findings == [
    ("ensure-unproven", 23, "guarded_arm"),
    ("ensure-unproven", 32, "payload_literal"),
    ("ensure-unproven", 41, "range_off_by_one"),
    ("ensure-unproven", 52, "after_guard_call"),
    ("ensure-unproven", 61, "later_arm"),
    ("ensure-unproven", 70, "pinned"),
    ("ensure-unproven", 74, "guarded_value"),
    ("pattern-unsupported", 28, "payload_literal"),
], findings
assert data["replay"]["gaps"] == 0, data["replay"]

print("match refuted arms: exact earlier patterns negated on later arms; inexact ones withheld")
