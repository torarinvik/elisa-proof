"""Inferred scalar tuples preserve checked summaries, never false claims."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")
root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))

def report(example, code):
    process = subprocess.run([binary, "--json", str(root / "examples" / example)],
                             capture_output=True, text=True, timeout=120)
    assert process.returncode == code, (example, process.returncode, process.stderr)
    data = json.loads(process.stdout)
    for section, fields in (("summary", ("semantic_errors", "obligations", "proven", "unproven")),
                            ("replay", ("certificates", "replayed", "gaps"))):
        for field in fields:
            counter = data[section][field]
            assert type(counter) is int and counter >= 0, (example, section, field, counter)
    assert data["summary"]["obligations"] == data["summary"]["proven"] + data["summary"]["unproven"]
    assert data["summary"]["semantic_errors"] == 0
    assert data["replay"]["gaps"] == 0
    assert data["replay"]["certificates"] == data["replay"]["replayed"] == data["summary"]["proven"]
    assert data["trust"]["trusted_assumptions"] == []
    return data

positive = report("inferred_tuple_summary_probe.elisa", 0)
assert positive["status"] == "proved" and positive["findings"] == []
assert positive["summary"]["obligations"] == positive["summary"]["proven"] > 0
assert {row["name"] for row in positive["declaration_details"]
        if row["kind"] == "function" and row["verified"]} == {
            "tuple_summary_source", "explicit_tuple_summary", "inferred_tuple_summary",
            "guarded_inferred_tuple_summary", "shadowed_inferred_tuple_guard"}
negative = report("rejected_inferred_tuple_summary.elisa", 1)
assert negative["status"] == "failed"
refused = {row["name"] for row in negative["findings"] if row["kind"] == "ensure-unproven"}
assert refused == {"wrong_inferred_tuple_value", "wrong_inferred_tuple_boolean",
                   "unverified_tuple_source", "unverified_inferred_tuple_value",
                   "stale_inferred_tuple_value"}
assert any(row["name"] == "stateful_tuple_source" and row["kind"] == "function"
           and row["verified"] for row in negative["declaration_details"])
assert any(row["name"] == "unverified_inferred_tuple_value"
           and row["kind"] == "function-summary-unverified" for row in negative["findings"])
print("inferred tuples: checked summaries replay; false claims, unchecked callees and stale state refuse")
