"""A lexical non-callable must not borrow a global tuple-return signature."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
process = subprocess.run(
    [binary, "--function-json", "shadowed_tuple_callee",
     str(root / "examples/rejected_tuple_callee_shadow.elisa")],
    capture_output=True, text=True, timeout=60)
assert process.returncode == 1, (process.returncode, process.stderr)
data = json.loads(process.stdout)
assert data["status"] == "failed"
summary, replay = data["summary"], data["replay"]
for section, fields in ((summary, ("obligations", "proven", "unproven", "semantic_errors")),
                        (replay, ("certificates", "replayed", "gaps"))):
    assert all(type(section[key]) is int and section[key] >= 0 for key in fields)
assert summary["semantic_errors"] > 0
assert summary["unproven"] > 0
assert summary["obligations"] == summary["proven"] + summary["unproven"]
assert replay["gaps"] == 0
assert replay["certificates"] == replay["replayed"] == summary["proven"]
rows = {row["name"]: row for row in data["declaration_details"]
        if row["kind"] == "function"}
assert rows["shadowed_tuple_callee"]["verified"] is False
assert rows["tuple_summary_source"]["verified"] is True
assert data["trust"]["trusted_assumptions"] == []
print("tuple callee shadow: invalid local call cannot inherit global verified summary")
