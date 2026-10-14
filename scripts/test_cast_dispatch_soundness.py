"""A source __cast__ hook must not inherit builtin numeric-cast proof facts."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

BINARY = Path(qualified_test_binary.proof_test_binary(ROOT))


def check(source):
    run = subprocess.run([str(BINARY), "--json", str(source)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode in (0, 1), (run.returncode, run.stderr, run.stdout)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    return data


custom = check(ROOT / "test/repro/audit_custom_cast_facts.elisa")
assert custom["status"] != "proved", custom
assert custom["replay"]["gaps"] == 0, custom["replay"]
assert custom["replay"]["certificates"] == custom["replay"]["replayed"], custom["replay"]
declarations = {item["name"]: item for item in custom["declaration_details"]
                if item.get("kind") == "function"}
assert declarations["__cast__"]["verified"], declarations["__cast__"]
for name in ("rejected_custom_cast_range", "rejected_custom_cast_identity",
             "rejected_custom_cast_monotonicity", "rejected_custom_cast_reference_write"):
    assert not declarations[name]["verified"], declarations[name]

# Neither producer certificates nor serialized goal contexts may carry a method-shaped cast as
# though the selector itself justified a builtin equation. The custom hook must remain opaque.
def contains_method_numeric_cast(expression):
    if not isinstance(expression, dict):
        return False
    if expression.get("kind") == "call":
        callee = expression.get("callee", {})
        field = callee.get("field") if callee.get("kind") == "field" else ""
        if field in {"i8", "i16", "i32", "i64", "isize", "u8", "u16", "u32", "u64", "usize"} and not expression.get("arguments"):
            return True
    if isinstance(expression, dict):
        return any(contains_method_numeric_cast(value) for value in expression.values())
    if isinstance(expression, list):
        return any(contains_method_numeric_cast(value) for value in expression)
    return False


for row in custom["certificates"] + custom["goals"]:
    assert not contains_method_numeric_cast(row.get("facts", [])), row
    assert not contains_method_numeric_cast(row.get("goal", {})), row

failed_goals = {row["name"]: row for row in custom["goals"]
                if row.get("rule") == "goal" and not row.get("proven")}
for name in ("rejected_custom_cast_range", "rejected_custom_cast_identity",
             "rejected_custom_cast_monotonicity", "rejected_custom_cast_reference_write"):
    assert name in failed_goals, (name, custom["goals"])

external = check(ROOT / "test/repro/audit_extern_custom_cast_facts.elisa")
external_function = next(item for item in external["declaration_details"]
                         if item.get("name") == "rejected_extern_custom_cast_identity")
assert not external_function["verified"], external_function
assert any(row.get("name") == "rejected_extern_custom_cast_identity"
           and row.get("rule") == "goal" and not row.get("proven")
           for row in external["goals"]), external["goals"]

# The pinned backend's cast-hook lookup scans the shared FnTable without filtering owner paths.
# A matching hook in a sibling module can therefore override the builtin scalar cast too.
sibling = check(ROOT / "test/repro/audit_sibling_module_custom_cast_facts.elisa")
assert sibling["status"] != "proved", sibling
assert sibling["replay"]["gaps"] == 0, sibling["replay"]
sibling_function = next(item for item in sibling["declaration_details"]
                        if item.get("name") == "rejected_sibling_custom_cast_identity")
assert not sibling_function["verified"], sibling_function
assert any(row.get("name") == "rejected_sibling_custom_cast_identity"
           and row.get("rule") == "goal" and not row.get("proven")
           for row in sibling["goals"]), sibling["goals"]

# Builtin cast syntax wins before ordinary UFCS lookup, even when a function has the target
# selector's spelling. This should preserve proof coverage while custom __cast__ hooks stay opaque.
selector = check(ROOT / "test/repro/audit_numeric_cast_selector_name.elisa")
assert selector["status"] == "proved", selector
assert selector["replay"]["gaps"] == 0, selector["replay"]
selector_function = next(item for item in selector["declaration_details"]
                         if item.get("name") == "ordinary_i64_selector_does_not_shadow_cast")
assert selector_function["verified"], selector_function
extern_selector_function = next(item for item in selector["declaration_details"]
                                if item.get("name") == "extern_u64_selector_does_not_shadow_cast")
assert extern_selector_function["verified"], extern_selector_function
for name in ("ordinary_i64_selector_does_not_shadow_cast",
             "extern_u64_selector_does_not_shadow_cast"):
    assert any(row.get("name") == name and row.get("rule") == "goal"
               and row.get("proven") and row.get("replayed")
               for row in selector["certificates"]), (name, selector["certificates"])

# Builtin control: with no custom hook, normal widening facts still prove and replay.
builtin = check(ROOT / "examples/widening_cast.elisa")
assert builtin["status"] in ("proved", "proved_with_replay_gaps"), builtin["status"]
for name in ("bare", "unsigned_to_unsigned"):
    assert any(c["name"] == name and c["rule"] == "goal" and c["replayed"]
               for c in builtin["certificates"]), (name, builtin["certificates"])

print("cast dispatch: custom hook assumptions rejected; builtin widening replays")
