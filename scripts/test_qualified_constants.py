"""Qualified module constants: `Module::CONST` in a contract is a traced, replay-validated fact.
Positive proofs, wrong-module and wrong-value refusals, and a parameter shadowing the module."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, data = run("qualified_constants.elisa")
assert code == 0 and data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["summary"]["proven"] == 6 and data["replay"]["gaps"] == 0

code, data = run("rejected_qualified_constants.elisa")
assert code == 1 and data["status"] == "failed"
assert sorted(f["name"] for f in data["findings"]) == ["wrong_module", "wrong_value"], data["findings"]
assert data["replay"]["gaps"] == 0

code, data = run("rejected_qualified_shadow.elisa")
assert code == 1 and data["status"] == "failed" and data["replay"]["gaps"] == 0, data["findings"]
assert [f["name"] for f in data["findings"]] == ["shadowed"], data["findings"]

code, data = run("qualified_constants_body.elisa")
assert code == 0 and data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["summary"]["proven"] == 4 and data["replay"]["gaps"] == 0

for name, function in (("rejected_qualified_constants_body.elisa", "too_small"),
                       ("rejected_qualified_body_shadow.elisa", "shadowed")):
    code, data = run(name)
    assert code == 1 and data["status"] == "failed" and data["replay"]["gaps"] == 0, data["findings"]
    assert [f["name"] for f in data["findings"]] == [function], data["findings"]

# BACKLOG B-06: assignments, call arguments, `while` conditions and loop contracts, `for` ranges.
# The one failure is the u8 `decreases` gap, independent of the constant (same with a literal).
code, data = run("qualified_constants_statements.elisa")
assert data["replay"]["gaps"] == 0 and data["summary"]["proven"] == 16, data["summary"]
assert [(f["name"], f["kind"]) for f in data["findings"]] == [("looped", "loop-decreases-unproven")], data["findings"]
code, data = run("rejected_qualified_constants_statements.elisa")
assert data["replay"]["gaps"] == 0
assert {f["name"] for f in data["findings"] if f["kind"] != "loop-decreases-unproven"} == {"assigned", "argument", "looped", "ranged"}, data["findings"]
code, data = run("rejected_qualified_statements_shadow.elisa")
assert data["replay"]["gaps"] == 0 and [(f["name"], f["kind"]) for f in data["findings"]] == [("shadowed", "call-requires-unproven")], data["findings"]

print("qualified constants: contract uses prove, wrong module/value/shadowing refuse")
