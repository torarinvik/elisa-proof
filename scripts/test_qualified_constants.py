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

print("qualified constants: contract uses prove, wrong module/value/shadowing refuse")
