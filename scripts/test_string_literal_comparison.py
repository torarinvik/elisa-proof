"""Check closed string literal equality and disequality with independent replay."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name, expected_code):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == expected_code, (name, result.returncode, result.stderr)
    data = json.loads(result.stdout)
    assert data["summary"]["semantic_errors"] == data["summary"]["semantic_diagnostics"] == 0, data
    assert data["replay"]["gaps"] == 0, data
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data
    assert data["trust"]["trusted_assumptions"] == [], data
    return data


positive = report("string_literal_comparison_contract.elisa", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert not positive["findings"], positive
verified = {item["name"] for item in positive["declaration_details"]
            if item["kind"] == "function" and item["verified"]}
assert verified == {"equal_string_literals", "distinct_string_literals",
                    "empty_string_literals_are_equal"}, positive

negative = report("rejected_string_literal_comparison_contract.elisa", 1)
assert negative["status"] == "failed" and negative["verification_state"] == "unknown", negative
unproven = {finding["name"] for finding in negative["findings"]
            if finding["kind"] == "ensure-unproven"}
assert unproven == {"wrong_equal_string_literals", "wrong_distinct_string_literals"}, negative
print("string literal equality/disequality replay exactly; false controls remain unproved")
