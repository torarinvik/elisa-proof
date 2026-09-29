"""Check module-local u8 constant substitution and independent fact replay."""
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


positive = report("module_u8_constant_contract.elisa", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert not positive["findings"], positive
negative = report("rejected_module_u8_constant_contract.elisa", 1)
assert negative["status"] == "failed" and negative["verification_state"] == "unknown", negative
assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong_action"
           and not f["counterexample_found"] for f in negative["findings"]), negative
signed = report("module_negative_i64_constant_contract.elisa", 0)
assert signed["status"] == signed["verification_state"] == "proved", signed
assert not signed["findings"], signed
wrong_signed = report("rejected_negative_i64_module_constant_contract.elisa", 1)
assert wrong_signed["status"] == "failed" and wrong_signed["verification_state"] == "unknown", wrong_signed
assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong_status"
           and not f["counterexample_found"] for f in wrong_signed["findings"]), wrong_signed
qualified = report("module_qualified_global_constant_contract.elisa", 0)
assert qualified["status"] == qualified["verification_state"] == "proved", qualified
assert not qualified["findings"], qualified
qualified_negative = report("rejected_qualified_global_constant_boundary.elisa", 1)
assert qualified_negative["status"] == "failed" and qualified_negative["verification_state"] == "unknown", qualified_negative
assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong_boundary"
           for f in qualified_negative["findings"]), qualified_negative
print("module-local u8, signed i64 and qualified constants preserve range/scope; false contracts stay open")
