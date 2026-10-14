"""Keep source-pattern literal lowering aligned with its replay admission guard."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(text: str, name: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"function {name} not found")


producer = (ROOT / "src/proof/check/pattern_lowering.elisa").read_text(encoding="utf-8")
replay = (ROOT / "src/proof/replay/boundary_pattern_fact_sources.elisa").read_text(encoding="utf-8")
replay_formal_type_find = function_body(replay, "proof_replay_control_pattern_source_formal_type_find")
assert "declaration_module <- function_module" in replay_formal_type_find
assert "function_module <- prior_module" in replay_formal_type_find
replay_formal_type = function_body(replay, "proof_replay_control_pattern_formal_type")
assert "&declaration_module" in replay_formal_type
assert "declaration_module, type_name, &replay_generic_work" in replay_formal_type
assert "proof_replay_control_pattern_source_formal_type_find" in replay_formal_type
assert "proof_replay_control_pattern_builtin_name_shadowed" in replay_formal_type
assert "proof_replay_control_pattern_builtin_import_shadowed" in replay_formal_type
assert "proof_pattern_source_formal_type_find" not in replay_formal_type
assert "proof_pattern_source_builtin_name_shadowed" not in replay_formal_type
assert "proof_pattern_source_builtin_import_shadowed" not in replay_formal_type
replay_name_shadow = function_body(replay, "proof_replay_control_pattern_builtin_name_shadowed")
assert "Ast::Decl.Alias" in replay_name_shadow and "Ast::Decl.Struct" in replay_name_shadow and "Ast::Decl.Enum" in replay_name_shadow
assert "proof_replay_control_pattern_source_text_equal" in replay_name_shadow
assert "owner_path[current_path.count]" in replay_name_shadow
assert "proof_replay_control_pattern_builtin_name_shadowed(nested, wanted, owner_path, current_path, work, depth + 1)" in replay_name_shadow
replay_formal_declaration_refusal = replay_formal_type.index("return Ast::Expr.Absent if not declaration_shadow.complete or declaration_shadow.shadowed")
assert replay_formal_declaration_refusal < replay_formal_type.index("proof_replay_control_pattern_builtin_import_shadowed")
replay_import_shadow = function_body(replay, "proof_replay_control_pattern_builtin_import_shadowed")
assert '"__binding_wildcard_import"' in replay_import_shadow
assert '"__from_member"' in replay_import_shadow and '"__using_alias"' in replay_import_shadow and '"__using_member"' in replay_import_shadow
assert "proof_replay_control_pattern_import_scope_visible(owner_path, annotation.module, work)" in replay_import_shadow
assert "proof_replay_control_pattern_builtin_import_shadowed(report.source.source_annotations, type_name, function_module_path, &bounded_work)" in replay_formal_type

string_guard = function_body(producer, "proof_pattern_unambiguous_string_literal_with_work")
assert "PROOF_PATTERN_STRING_LITERAL_SCAN_LIMIT" in string_guard
assert "length * 4 + 1" in string_guard
assert '"true" | "false" | "null"' in string_guard
assert "character == 34 or character == PROOF_ASCII_BACKSLASH" in string_guard
char_guard = function_body(producer, "proof_pattern_unambiguous_char_literal")
assert "length < 3" in char_guard
assert "character >= 32 and character <= 126" in char_guard
assert "interior_length == 2" in char_guard
assert "return false" in char_guard

typed_literal = function_body(producer, "proof_pattern_typed_literal_expression")
assert "proof_pattern_unambiguous_string_literal_with_work(text, source_work)" in typed_literal
assert "proof_pattern_unambiguous_char_literal(text)" in typed_literal
assert "Ast::Expr.StringLit(text, position)" in typed_literal
assert "Ast::Expr.CharLit(string_view_slice(text, 1, sview_len(text) - 1), position)" in typed_literal
assert ".i64()" not in typed_literal
formal_type_find = function_body(producer, "proof_pattern_source_formal_type_find")
assert "declaration_module <- function_module" in formal_type_find
assert "function_module <- prior_module" in formal_type_find
formal_type = function_body(producer, "proof_pattern_source_formal_type")
assert "&declaration_module" in formal_type
assert "declaration_module, type_name, work" in formal_type

# A builtin-looking type spelling is not enough to authenticate runtime representation.
formal_type = function_body(producer, "proof_pattern_source_formal_type")
assert "proof_pattern_source_builtin_name_shadowed" in formal_type
assert "proof_pattern_source_builtin_import_shadowed" in formal_type
declaration_refusal = formal_type.index("return Ast::Expr.Absent if not declaration_shadow.complete or declaration_shadow.shadowed")
assert declaration_refusal < formal_type.index("proof_pattern_source_builtin_import_shadowed")
name_shadow = function_body(producer, "proof_pattern_source_builtin_name_shadowed")
assert "Ast::Decl.Alias" in name_shadow and "Ast::Decl.Struct" in name_shadow and "Ast::Decl.Enum" in name_shadow
assert "proof_pattern_charge_source_type_work" in name_shadow
assert "owner_path[current_path.count]" in name_shadow
assert "proof_pattern_source_builtin_name_shadowed(nested, wanted, owner_path, current_path, work, depth + 1)" in name_shadow
assert "function_module_path" in formal_type
import_shadow = function_body(producer, "proof_pattern_source_builtin_import_shadowed")
assert '"__binding_wildcard_import"' in import_shadow
assert '"__from_member"' in import_shadow and '"__using_alias"' in import_shadow and '"__using_member"' in import_shadow
assert "proof_pattern_source_import_scope_visible(owner_path, annotation.module, work)" in import_shadow
assert "proof_pattern_source_builtin_import_shadowed(report.source.source_annotations, type_name, function_module_path, work)" in formal_type
shadow_regression = (ROOT / "scripts/test_pattern_builtin_shadow.py").read_text(encoding="utf-8")
assert "type sview = u64" in shadow_regression
assert "SIBLING_SHADOW_SOURCE" in shadow_regression
assert "module Owner:" in shadow_regression and "module Sibling:" in shadow_regression
assert "from Imported import char" in shadow_regression and "module Imported:" in shadow_regression
assert "OWNER_IMPORT_SHADOW_SOURCE" in shadow_regression
assert 'row["name"] == "imported_char_pattern" and row["kind"] == "ensure-unproven"' in shadow_regression
assert "builtin_char_pattern" in shadow_regression
assert 'row["name"] == "Owner" and row["proved"]' in shadow_regression
assert "--function-json" in shadow_regression and "ensure-unproven" in shadow_regression
# Fixed-width range probes stay connected to the executable collision matrix.
fixed_width_cases = (ROOT / "scripts/pattern_literal_fixed_width_cases.py").read_text(encoding="utf-8")
collision_matrix = (ROOT / "scripts/test_pattern_literal_collisions.py").read_text(encoding="utf-8")
assert "generic_nested_char_type_parameter" in collision_matrix
assert "PATTERN_COLLISIONS.update(FIXED_WIDTH_PATTERN_COLLISIONS)" in collision_matrix
for case in (
    "u8_high_bit_range_collision",
    "u16_high_bit_range_collision",
    "u32_high_bit_range_collision",
    "u64_high_bit_range_collision",
    "i8_signed_negative_range_collision",
    "i16_signed_zero_crossing_range_collision",
    "i64_signed_negative_range_collision",
):
    assert f"'{case}'" in fixed_width_cases
for range_literal in (
    "127u8..=128u8",
    "32767u16..=32768u16",
    "2147483647u32..=2147483648u32",
    "9223372036854775807u64..=9223372036854775808u64",
    "-128i8..=-127i8",
    "-1i16..=1i16",
    "-9223372036854775808i64..=-9223372036854775807i64",
):
    assert range_literal in fixed_width_cases
assert "FIXED_WIDTH_RANGE_CONTROLS" in fixed_width_cases
assert "FIXED_WIDTH_RANGE_CONTROLS.values()" in collision_matrix
assert "for name in FIXED_WIDTH_RANGE_CONTROLS:" in collision_matrix
for endpoint in (
    '"u64", "u64", "9223372036854775807u64", "9223372036854775808u64"',
    '"i64", "i64", "-9223372036854775808i64", "-9223372036854775807i64"',
):
    assert endpoint in fixed_width_cases
assert "requires value == {endpoint}" in fixed_width_cases
assert "ensure result == 1" in fixed_width_cases

pattern_shard = (ROOT / "scripts/test.d/02-patterns-and-constructors.sh").read_text(encoding="utf-8")
assert "run_py_test test_pattern_builtin_shadow.py" in pattern_shard

# Untyped matching must not turn erased token kinds into equality propositions.
untyped_condition = function_body(producer, "proof_pattern_condition_depth")
literal_arm = untyped_condition.split("Ast::Pattern.Literal", 1)[1].split("Ast::Pattern.Range", 1)[0]
assert "Ast::Expr.StringLit" not in literal_arm
assert "Ast::Expr.CharLit" not in literal_arm
typed_condition = function_body(producer, "proof_pattern_condition_typed_depth")
assert "proof_pattern_typed_literal_expression(text, position, type_expression, source_work)" in typed_condition
assert "return null" in typed_condition.split("Ast::Pattern.Range", 1)[1].split("Ast::Pattern.Or", 1)[0]

pattern_check = function_body(replay, "proof_replay_control_pattern_condition")
preflight = pattern_check.index("proof_replay_control_pattern_repeat_charge(pattern, 3, work)")
scan_reserve = pattern_check.index("proof_replay_control_pattern_string_scans_reserve(pattern, type_expression, 2, 0, work)")
typed_guard = pattern_check.index("proof_replay_control_pattern_typed_payload_unambiguous(pattern, type_expression)")
lowering = pattern_check.index("proof_pattern_condition_typed(pattern, scrutinee, position, type_expression)")
assert preflight < scan_reserve < typed_guard < lowering
scan_cost = function_body(replay, "proof_replay_control_pattern_string_scan_reserve")
assert "length * 4 + 1" in scan_cost
assert "scan_work > remaining / repetitions" in scan_cost
scan_walk = function_body(replay, "proof_replay_control_pattern_string_scans_reserve")
assert "Ast::Pattern.Literal(text)" in scan_walk
assert "Ast::Pattern.As(_, inner)" in scan_walk and "Ast::Pattern.Or(options)" in scan_walk
assert "proof_replay_control_pattern_string_scans_reserve(inner[0]" in scan_walk
assert "proof_replay_control_pattern_string_scans_reserve(option" in scan_walk
exactness_cost = function_body(replay, "proof_replay_control_pattern_exactness_work_charge")
assert "proof_replay_control_pattern_string_scan_reserve(text, 2, work)" in exactness_cost
branch_replay = (ROOT / "src/proof/replay/boundary_branch_fact_sources.elisa").read_text(encoding="utf-8")
exactness_call = "proof_replay_control_pattern_exactness_work_charge(prior.pattern, pattern_type, 0, work)"
exact_call = "proof_replay_control_pattern_exact(prior.pattern, pattern_type)"
assert exactness_call in branch_replay and branch_replay.index(exactness_call) < branch_replay.index(exact_call)
exact_check = function_body(replay, "proof_replay_control_pattern_exact")
assert "proof_replay_control_pattern_typed_payload_unambiguous(pattern, type_expression)" in exact_check
assert "proof_pattern_condition_exact_typed(pattern, type_expression)" in exact_check
assert "proof_replay_control_pattern_needs_source_type(pattern)" in exact_check

print("pattern literal source guards: bounded typed literals and replay preflight remain aligned")
