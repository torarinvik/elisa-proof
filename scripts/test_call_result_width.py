"""A returned call-bound local keeps its call's summary, a closed constant beside a call result
is read at the callee's declared signed width, and a call result nested in another call's
arguments generalizes with it; nothing else is."""
import json
from pathlib import Path
import subprocess
from qualified_test_binary import proof_test_binary

ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)


def check(name):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                         capture_output=True, text=True, timeout=60)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["source"]["admissible"] is True, data["source"]
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
    assert not data["trust"]["trusted_assumptions"], data["trust"]
    return run.returncode, data


def unproven(data):
    return sorted({(f["kind"], f["line"], f["name"]) for f in data["findings"]})


for name, minimum in (("call_result_width.elisa", 19), ("returned_call_local.elisa", 9),
                      ("nested_call_results.elisa", 12)):
    code, data = check(name)
    assert code == 0 and data["status"] == "proved", (name, code, data["findings"])
    assert data["findings"] == [], (name, data["findings"])
    assert data["replay"]["certificates"] >= minimum, (name, data["replay"])

for name in ("call_result_module_alias_u32.elisa", "call_result_local_precedence.elisa",
             "call_result_bare_imports_u16_u32.elisa"):
    code, data = check(name)
    assert code == 0 and data["status"] == "proved", (name, code, data["findings"])
    assert data["findings"] == [], (name, data["findings"])

code, data = check("rejected_call_result_width.elisa")
assert code == 1 and data["status"] == "failed", code
assert unproven(data) == [
    ("ensure-unproven", 24, "signed_wraps"),
    ("ensure-unproven", 29, "unsigned_wraps"),
    ("ensure-unproven", 35, "off_by_one"),
    ("ensure-unproven", 36, "off_by_one"),
    ("ensure-unproven", 41, "direct_call_off_by_one"),
    ("ensure-unproven", 48, "impure_call_untyped"),
], unproven(data)

code, data = check("rejected_returned_call_local.elisa")
assert code == 1 and data["status"] == "failed", code
assert unproven(data) == [
    ("call-requires-unproven", 36, "unproven_precondition"),
    ("ensure-unproven", 23, "stronger_than_the_summary"),
    ("ensure-unproven", 31, "referenced_value_must_not_survive"),
    ("ensure-unproven", 37, "unproven_precondition"),
], unproven(data)

code, data = check("rejected_nested_call_results.elisa")
assert code == 1 and data["status"] == "failed", code
assert unproven(data) == [
    ("ensure-unproven", 13, "distinct_inner"),
    ("ensure-unproven", 20, "strict_claim"),
    ("ensure-unproven", 26, "reversed_chain"),
    ("ensure-unproven", 32, "swapped_arguments"),
], unproven(data)

code, data = check("rejected_relative_module_type_width.elisa")
assert code == 1 and data["status"] == "failed", code
assert data["source"]["admissible"] is True, data["source"]
assert data["summary"]["semantic_errors"] == 0, data["semantic_diagnostics"]
assert data["replay"]["gaps"] == 0, data["replay"]
assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
assert not data["trust"]["trusted_assumptions"], data["trust"]
assert sorted((finding["kind"], finding["line"], finding["name"])
              for finding in data["findings"]) == [
    ("ensure-unproven", 22, "local_parameter_scope_collision"),
    ("ensure-unproven", 26, "call_result_scope_collision"),
    ("ensure-unproven", 59, "deep_local_parameter_scope_collision"),
    ("ensure-unproven", 63, "deep_call_result_scope_collision"),
    ("ensure-unproven", 119, "module_alias_type_path_refusal"),
    ("ensure-unproven", 123, "module_alias_parameter_type_path_refusal"),
    ("ensure-unproven", 133, "generic_result_primitive_name_shadow"),
], data["findings"]
assert any(row["name"] == "root_qualified_type_positive" and row["proved"]
           for row in data["functions"]), data["functions"]
assert any(row["name"] == "parent_module_parameter_fallback" and row["proved"]
           for row in data["functions"]), data["functions"]
assert any(row["name"] == "parent_module_call_result_fallback" and row["proved"]
           for row in data["functions"]), data["functions"]
assert any(row["name"] == "deep_local_parameter_width_positive" and row["proved"]
           for row in data["functions"]), data["functions"]
assert any(row["name"] == "deep_call_result_width_positive" and row["proved"]
           for row in data["functions"]), data["functions"]
assert any(row["name"] == "partial_parent_module_parameter_fallback" and row["proved"]
           for row in data["functions"]), data["functions"]
assert any(row["name"] == "partial_parent_module_call_result_fallback" and row["proved"]
           for row in data["functions"]), data["functions"]
assert any(row["name"] == "root_overload_after_incompatible_generic" and row["proved"]
           for row in data["functions"]), data["functions"]

code, data = check("rejected_call_result_shadowed_u32.elisa")
assert code == 1 and data["status"] == "failed", code
assert unproven(data) == [
    ("ensure-unproven", 13, "uses_local_forward_declaration"),
], unproven(data)

print("call results: returned locals keep their summary, constants typed at the call's width, nested and module-alias calls replayed, and shadowed forward calls rejected")
