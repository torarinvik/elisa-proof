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
assert negative["status"] == "failed" and negative["verification_state"] == "disproved", negative
assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong_action"
           and f["status"] == "disproved" and f["counterexample_found"] for f in negative["findings"]), negative
signed = report("module_negative_i64_constant_contract.elisa", 0)
assert signed["status"] == signed["verification_state"] == "proved", signed
assert not signed["findings"], signed
wrong_signed = report("rejected_negative_i64_module_constant_contract.elisa", 1)
assert wrong_signed["status"] == "failed" and wrong_signed["verification_state"] == "disproved", wrong_signed
assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong_status"
           and f["status"] == "disproved" and f["counterexample_found"] for f in wrong_signed["findings"]), wrong_signed
qualified = report("module_qualified_global_constant_contract.elisa", 0)
assert qualified["status"] == qualified["verification_state"] == "proved", qualified
assert not qualified["findings"], qualified
qualified_negative = report("rejected_qualified_global_constant_boundary.elisa", 1)
assert qualified_negative["status"] == "failed" and qualified_negative["verification_state"] == "unknown", qualified_negative
assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong_boundary"
           for f in qualified_negative["findings"]), qualified_negative
extended = report("extend_qualified_u8_return.elisa", 0)
assert extended["status"] == extended["verification_state"] == "proved", extended
assert not extended["findings"], extended
assert any(d["name"] == "interval_status" and d["verified"] and d["ensures"] == 1
           for d in extended["declaration_details"]), extended
extended_negative = report("rejected_extend_qualified_u8_return.elisa", 1)
assert extended_negative["status"] == "failed", extended_negative
assert extended_negative["summary"]["semantic_errors"] == 0, extended_negative
assert extended_negative["replay"]["gaps"] == 0, extended_negative
assert extended_negative["replay"]["certificates"] == extended_negative["replay"]["replayed"], extended_negative
assert any(f["kind"] == "ensure-unproven" and f["name"] == "interval_status_wrong_bound"
           for f in extended_negative["findings"]), extended_negative
extension_local = report("extend_scope_local_u8_constant.elisa", 0)
assert extension_local["status"] == extension_local["verification_state"] == "proved", extension_local
assert not extension_local["findings"], extension_local
assert any(d["name"] == "interval_status" and d["verified"] and d["ensures"] == 1
           for d in extension_local["declaration_details"]), extension_local
extension_local_negative = report("rejected_extend_scope_local_u8_constant.elisa", 1)
assert extension_local_negative["status"] == "failed", extension_local_negative
assert extension_local_negative["summary"]["semantic_errors"] == 0, extension_local_negative
assert extension_local_negative["replay"]["gaps"] == 0, extension_local_negative
assert extension_local_negative["replay"]["certificates"] == extension_local_negative["replay"]["replayed"], extension_local_negative
assert any(f["kind"] == "ensure-unproven" and f["name"] == "interval_status_wrong_bound"
           for f in extension_local_negative["findings"]), extension_local_negative
timer_error_map = report("extend_timer_wit_error_tag_bound.elisa", 0)
assert timer_error_map["status"] == timer_error_map["verification_state"] == "proved", timer_error_map
assert not timer_error_map["findings"], timer_error_map
assert any(d["name"] == "timer_wit_error_tag" and d["verified"] and d["ensures"] == 2
           for d in timer_error_map["declaration_details"]), timer_error_map
scoped_branch_bound = report("extend_scoped_constant_branch_bound.elisa", 0)
assert scoped_branch_bound["status"] == scoped_branch_bound["verification_state"] == "proved", scoped_branch_bound
assert not scoped_branch_bound["findings"], scoped_branch_bound
assert any(d["name"] == "map_status" and d["verified"] and d["ensures"] == 1
           for d in scoped_branch_bound["declaration_details"]), scoped_branch_bound
u32_branch = report("module_u32_scoped_constant_branch.elisa", 0)
assert u32_branch["status"] == u32_branch["verification_state"] == "proved", u32_branch
assert not u32_branch["findings"], u32_branch
assert any(d["name"] == "delay_status" and d["verified"] and d["ensures"] == 1
           for d in u32_branch["declaration_details"]), u32_branch
wrong_u32_branch = report("rejected_module_u32_scoped_constant_branch.elisa", 1)
assert wrong_u32_branch["status"] == "failed" and wrong_u32_branch["verification_state"] == "disproved", wrong_u32_branch
assert any(f["kind"] == "ensure-unproven" and f["name"] == "delay_status"
           and f["status"] == "disproved" and f["counterexample_found"]
           for f in wrong_u32_branch["findings"]), wrong_u32_branch
print("module-local u8/u32, signed, qualified and many-constant contracts replay; false controls stay open")
