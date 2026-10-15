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
assert "nested_path.scope.count > owner_path.count" in replay_name_shadow
assert "nested_path.scope[index], owner_path[index]" in replay_name_shadow
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
assert "character == 34 or character == PROOF_ASCII_BACKSLASH" in string_guard
assert "first_letter" not in string_guard
assert "reserved_literal_spelling" not in string_guard
collision_tests = (ROOT / "scripts/test_pattern_literal_collisions.py").read_text(encoding="utf-8")
assert "AMBIGUOUS_SPELLING_STRING_PATTERN_CONTROLS" in collision_tests
assert "sview_escaped_newline_pattern_refused" in collision_tests
assert '"line\\\\n"' in collision_tests
for literal_text in ('"01"', '"0x1"', '"true"', '"null"'):
    assert literal_text in collision_tests
boolean_collision_tests = (ROOT / "scripts/pattern_literal_boolean_cases.py").read_text(encoding="utf-8")
for boolean_collision in ('bool_true_pattern_collision', 'bool_false_pattern_collision'):
    assert boolean_collision in boolean_collision_tests
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
assert "nested_path.count > owner_path.count" in name_shadow
assert "nested_path[index] != owner_path[index]" in name_shadow
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
local_collision_cases = (ROOT / "scripts/pattern_literal_local_collision_cases.py").read_text(encoding="utf-8")
collision_matrix += local_collision_cases
assert "generic_nested_char_type_parameter" in collision_matrix
assert "PATTERN_COLLISIONS.update(FIXED_WIDTH_PATTERN_COLLISIONS)" in collision_matrix
for local_collision in (
    "sview_local_01_vs_1_collision",
    "cstr_local_hex_vs_decimal_collision",
    "u64_local_high_bit_literal_collision",
):
    assert f"'{local_collision}': '''" in collision_matrix
assert "value: sview = \"01\"" in collision_matrix
assert "value: cstr = \"0x1\"" in collision_matrix
assert "value: u64 = 9223372036854775808u64" in collision_matrix
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
assert "not report.source.source_operator_masks_valid" in pattern_check
typed_guard = pattern_check.index("proof_replay_control_pattern_condition_typed_with_work(pattern, scrutinee, position, type_expression, 0, work)")
lowering = pattern_check.index("proof_replay_control_pattern_condition_typed_with_work(pattern, scrutinee, position, type_expression")
assert preflight < typed_guard <= lowering
typed_replay_lowering = function_body(replay, "proof_replay_control_pattern_condition_typed_with_work")
assert "Ast::Expr.StringLit(text, position)" in typed_replay_lowering
assert "Ast::Expr.CharLit(string_view_slice(text, 1, sview_len(text) - 1), position)" in typed_replay_lowering
assert "proof_pattern_condition_typed(" not in typed_replay_lowering
assert "proof_pattern_unambiguous_string_literal" not in replay
assert "proof_pattern_unambiguous_char_literal" not in replay
replay_string_guard = function_body(replay, "proof_replay_control_pattern_unambiguous_string_with_work")
assert "character < 32 or character > 126 or character == 34 or character == 92" in replay_string_guard
assert "work <- work + length * 4 + 1" in replay_string_guard
replay_char_guard = function_body(replay, "proof_replay_control_pattern_unambiguous_char")
assert "character >= 32 and character <= 126" in replay_char_guard
assert "escaped == 110 or escaped == 116 or escaped == 114 or escaped == 48" in replay_char_guard
branch_replay = (ROOT / "src/proof/replay/boundary_branch_fact_sources.elisa").read_text(encoding="utf-8")
exact_call = "proof_replay_control_pattern_exact(prior.pattern, pattern_type, work)"
assert exact_call in branch_replay
exact_check = function_body(replay, "proof_replay_control_pattern_exact")
assert "proof_replay_control_pattern_exact_typed_with_work(pattern, type_expression, 0, work)" in exact_check
typed_replay_exactness = function_body(replay, "proof_replay_control_pattern_exact_typed_with_work")
assert "proof_pattern_condition_exact_typed(" not in typed_replay_exactness
assert "proof_replay_control_pattern_needs_source_type(pattern)" in exact_check
typed_pattern_replay = function_body(replay, "proof_replay_control_pattern_condition")
assert "proof_source_expression_has_overloaded_operator(expression, report.source.source_primitive_operator_mask, 0)" in typed_pattern_replay
assert "custom literal comparisons cannot enter through a user operator" in typed_pattern_replay
overloaded_eq_cases = (ROOT / "scripts/pattern_literal_overloaded_eq_case.py").read_text(encoding="utf-8")
assert "PATTERN_COLLISIONS.update(STRING_EQ_OVERRIDE_COLLISIONS)" in collision_tests
assert "STRING_EQ_OVERRIDE_PRELUDE" in collision_tests
assert "impl Less for sview" in overloaded_eq_cases and "def __eq__(self: sview" in overloaded_eq_cases
assert "impl Eq for cstr" in overloaded_eq_cases
assert "impl Eq for i64" in overloaded_eq_cases and "impl Eq for u64" in overloaded_eq_cases
assert "impl Eq for i8" in overloaded_eq_cases and "impl Eq for u8" in overloaded_eq_cases
assert "sview_pattern_overloaded_eq_collision" in overloaded_eq_cases
assert "cstr_pattern_overloaded_eq_collision" in overloaded_eq_cases
assert "i64_pattern_overloaded_eq_collision" in overloaded_eq_cases
assert "u64_pattern_overloaded_eq_collision" in overloaded_eq_cases
assert "i8_pattern_overloaded_eq_collision" in overloaded_eq_cases
assert "u8_pattern_overloaded_eq_collision" in overloaded_eq_cases
for fixture_name, type_name in (("sview_pattern_overloaded_eq_collision", "sview"),
                                ("cstr_pattern_overloaded_eq_collision", "cstr"),
                                ("i64_pattern_overloaded_eq_collision", "i64"),
                                ("u64_pattern_overloaded_eq_collision", "u64"),
                                ("i8_pattern_overloaded_eq_collision", "i8"),
                                ("u8_pattern_overloaded_eq_collision", "u8")):
    fixture_start = overloaded_eq_cases.index(f"    '{fixture_name}': '''")
    fixture_end = overloaded_eq_cases.index("''',", fixture_start)
    fixture = overloaded_eq_cases[fixture_start:fixture_end]
    assert f"def {fixture_name}(value: {type_name}) -> bool:" in fixture
    assert "ensure result == true" in fixture and "match value:" in fixture
    expected_literal = '"needle"' if type_name in ("sview", "cstr") else "7"
    assert f"        {expected_literal}:" in fixture
    assert f"return value == {expected_literal}" in fixture

print("pattern literal source guards: bounded typed literals and replay preflight remain aligned")
