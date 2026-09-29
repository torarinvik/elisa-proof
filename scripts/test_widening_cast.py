"""A widening integer conversion keeps its receiver's value; nothing else does."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def check(name):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                         capture_output=True, text=True, timeout=60)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
    return run.returncode, data


code, data = check("widening_cast.elisa")
assert code == 0 and data["status"] == "proved", (code, data["findings"])
assert data["findings"] == [], data["findings"]
assert data["replay"]["certificates"] >= 36, data["replay"]

code, data = check("rejected_widening_cast.elisa")
assert code == 1 and data["status"] == "failed", code
unproven = sorted({(f["line"], f["name"]) for f in data["findings"] if f["kind"] == "ensure-unproven"})
assert unproven == [
    (9, "narrowed"),
    (14, "signed_to_unsigned"),
    (19, "unsigned_to_signed"),
    (24, "signed_widen_below"),
    (29, "widened_above"),
    (44, "method_named_cast"),
], unproven
assert not any(goal["proven"] for goal in data["goals"] if goal["rule"] == "goal"), data["goals"]

print("widening casts: value kept through widening conversions only, replayed")
