"""Verified pure helpers may appear in pure functions' postconditions."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(path):
    run = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True,
                         text=True, timeout=60)
    data = json.loads(run.stdout)
    assert run.returncode == 0 and data["status"] == "proved", data["findings"]
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
    return data


accepted = report(ROOT / "examples/pure_postcondition_calls.elisa")
functions = {item["name"]: item for item in accepted["declaration_details"]
             if item.get("kind") == "function"}
for name in ("postcondition_call_base", "postcondition_call_derived",
             "postcondition_call_consumer"):
    assert functions[name]["pure"] and functions[name]["verified"], functions[name]

rejected_run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/rejected_contract_call.elisa")],
    capture_output=True, text=True, timeout=60)
rejected = json.loads(rejected_run.stdout)
assert rejected_run.returncode == 1 and rejected["status"] == "failed", rejected
assert rejected["verification_state"] == "unsupported", rejected
assert any(item["kind"] == "contract-call-unsupported"
           for item in rejected["findings"]), rejected["findings"]
assert rejected["replay"]["gaps"] == 0, rejected["replay"]

print("pure postcondition calls: pure summaries compose and impure calls stay rejected")
