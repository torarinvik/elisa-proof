"""`ensures` is the plural postcondition head: checked on every return and read by callers."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name, expected_status):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / f"{name}.elisa")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected_status, (name, run.returncode, run.stderr, run.stdout)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["replay"]["gaps"] == 0, data
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data
    return data


accepted = report("body_ensures", 0)
assert accepted["status"] == "proved", accepted
assert accepted["findings"] == [], accepted["findings"]
functions = {d["name"]: d for d in accepted["declaration_details"] if d.get("kind") == "function"}
for name in ("plural_on_every_return", "plural_summary", "caller_reads_plural", "both_spellings"):
    assert functions[name]["verified"], functions[name]

rejected = report("rejected_body_ensures", 1)
assert rejected["status"] == "failed", rejected
found = sorted((f["line"], f["name"], f["kind"]) for f in rejected["findings"])
assert found == [
    (5, "plural_false", "ensure-unproven"),
    (6, "plural_false", "ensure-unproven"),
    (12, "plural_beside_true", "ensure-unproven"),
], found

print("body ensures: the plural head is checked on every return and read by callers")
