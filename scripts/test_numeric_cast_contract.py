"""Verified primitive numeric casts are pure contract terms, not effectful calls."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name: str, expected_exit: int) -> dict:
    source = ROOT / f"examples/{name}.elisa"
    run = subprocess.run([str(BINARY), "--json", str(source)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected_exit, (name, run.returncode, run.stderr, run.stdout)
    return json.loads(run.stdout)


positive = report("numeric_cast_contract", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
functions = {item["name"]: item for item in positive["declaration_details"]
             if item.get("kind") == "function"}
assert functions["status_cast_is_reflexive"]["verified"], functions
assert functions["status_cast_is_reflexive"]["ensures"] == 1, functions

negative = report("rejected_effectful_numeric_cast_contract", 1)
assert negative["status"] == "failed", negative
assert negative["verification_state"] == "unsupported", negative
assert negative["summary"]["semantic_errors"] == 0, negative
assert any(finding["kind"] == "contract-call-unsupported"
           and finding["name"] == "rejected_effectful_status_cast"
           for finding in negative["findings"]), negative

print("numeric-cast contracts: primitive conversion proved; effectful receiver rejected")
