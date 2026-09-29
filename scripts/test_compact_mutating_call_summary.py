"""Small low-arity contracts stay bounded and mutating call summaries replay."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name: str, expected: int) -> dict:
    result = subprocess.run(
        [str(BINARY), "--json", str(ROOT / f"examples/{name}.elisa")],
        capture_output=True, text=True, timeout=60)
    assert result.returncode == expected, (name, result.returncode, result.stderr)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == 0, (name, report["findings"])
    assert report["replay"]["gaps"] == 0, (name, report["replay"])
    assert report["replay"]["certificates"] == report["replay"]["replayed"], name
    assert report["trust"]["trusted_assumptions"] == [], name
    return report


positive = run("compact_mutating_call_summary", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive["summary"]
assert positive["summary"]["proven"] == positive["summary"]["obligations"]
functions = {entry["name"]: entry for entry in positive["declaration_details"]
             if entry.get("kind") == "function"}
assert functions["decode_status"]["verified"] and functions["decode_status"]["ensures"] == 5
assert functions["wrapper_status"]["verified"] and functions["wrapper_status"]["ensures"] == 5
assert any(trace["kind"] == "function-summary" and
           trace["dependency"] == "decode_status" and
           trace["name"] == "wrapper_status"
           for trace in positive["kernel"]["fact_traces"])

negative = run("rejected_compact_mutating_call_summary", 1)
assert negative["status"] == "failed" and negative["verification_state"] == "unknown", negative["summary"]
assert any(finding["kind"] == "ensure-unproven" and
           finding["name"] == "rejected_wrapper_status"
           for finding in negative["findings"]), negative["findings"]

print("compact mutating call summary: bounded status/output contracts and summary replay pass; false mapping rejected")
