"""Guard generic type alias applications through source type normalization."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ROOT / "src/proof/check/source_conversion_alias_resolution.elisa",
    ROOT / "src/proof/check/source_conversion_generic_alias_application.elisa",
    ROOT / "src/proof/check/source_conversion_type_aliases.elisa",
    ROOT / "src/proof/replay/source_call_type_aliases.elisa",
    ROOT / "src/proof/replay/source_call_type_argument_shape.elisa",
)


def function_body(name: str) -> str:
    for source in SOURCES:
        lines = source.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if re.match(rf"\s*def {re.escape(name)}\b", line):
                indent = len(line) - len(line.lstrip())
                body = [line]
                for following in lines[index + 1 :]:
                    if following.strip() and len(following) - len(following.lstrip()) <= indent:
                        break
                    body.append(following)
                return "\n".join(body)
    raise AssertionError(f"function {name} not found")


unwrap = function_body("proof_source_conversion_type_alias_unwrap_with_formals")
assert "Ast::Expr.Index(head, element, position):" in unwrap
assert "Ast::Expr.IndexN(head, arguments, position):" in unwrap
assert unwrap.count("proof_source_conversion_alias_application_target(head, resolution_owner, resolution_owner_known, report)") == 2
assert unwrap.count("proof_source_conversion_type_alias_expand_applied(application.row, application.target, actuals, report, seen, depth)") == 2
assert unwrap.count("proof_source_conversion_type_alias_unwrap_with_formals(") >= 3
assert unwrap.count("proof_source_conversion_alias_type_expression_safe(") >= 2
assert "index.aliases.alias_generic_formal_counts[application.row] != arguments.count" in unwrap

applied = function_body("proof_source_conversion_type_alias_expand_applied")
assert "actuals.count != index.aliases.alias_generic_formal_counts[row]" in applied
assert "index.aliases.alias_generic_application_valid[row] == false" in applied
assert "index.aliases.alias_owners[row]" in applied

alias_validation = function_body("proof_source_conversion_generic_alias_bodies_validate")
assert alias_validation.index("proof_report_source_work_charge(index.aliases.alias_names.count, source_work)") < alias_validation.index("generic_alias_safe.resize")
assert "proof_source_conversion_alias_type_formals_safe(alias_row, &active_rows, report, 0)" in alias_validation
assert "index.aliases.alias_generic_application_valid[alias_row] <- generic_alias_safe[alias_row]" in alias_validation

index_build = function_body("proof_source_conversion_indexes_build")
assert index_build.index("index.callables.callable_scope_index_valid <- true") < index_build.index("proof_source_conversion_generic_alias_bodies_validate(report, source_work)")
assert "index.aliases.alias_generic_application_valid.clear()" in index_build

replay_application = function_body("proof_replay_call_conversion_alias_application_target")
global_name_fallback = replay_application.split("alias: (complete: bool, count: usize, row: usize) = proof_replay_call_conversion_name_lookup(name, aliases", 1)[1]
global_name_fallback = global_name_fallback.split("Ast::Expr.Scope(parent, name, _):", 1)[0]
assert "nominal.count > 0" in global_name_fallback
assert global_name_fallback.index("nominal.count > 0") < global_name_fallback.index("return (true, true, alias.row")

actual_shape = function_body("proof_replay_call_conversion_type_argument_shape_safe")
scope_shape = actual_shape.split("Ast::Expr.Scope(parent, name, _):", 1)[1].split("Ast::Expr.Paren(inner, _):", 1)[0]
assert "proof_replay_call_conversion_generic_root(parent, work, 0)" in scope_shape
assert "proof_replay_call_conversion_alias_formal_head(root.name, formal_owner_row, call_target, work)" in scope_shape
assert "not formal_head.complete or formal_head.found" in scope_shape
assert "proof_replay_call_conversion_non_generic_alias_target_shape_safe(qualified.row, qualified.target" in scope_shape

non_generic_body = function_body("proof_replay_call_conversion_non_generic_alias_target_shape_safe")
assert "not proof_replay_call_conversion_alias_work_add(work, 1)" in non_generic_body
assert "aliases.field_conversion_alias_has_formals[row]" in non_generic_body
assert "proof_replay_call_conversion_type_argument_shape_safe(target," in non_generic_body

replay_builtin_head = function_body("proof_replay_call_conversion_builtin_generic_type_head")
assert 'name != "darray" and name != "view" and name != "array"' in replay_builtin_head
assert "proof_replay_call_conversion_alias_target_in_owner(name, resolution_owner" in replay_builtin_head
assert 'proof_replay_call_conversion_alias_target_in_owner(name, ""' in replay_builtin_head
assert "proof_replay_call_conversion_alias_target(name, call_target, work)" in replay_builtin_head
assert "owner_target.blocks_parent" in replay_builtin_head
assert "root_target.blocks_parent" in replay_builtin_head
shape = function_body("proof_replay_call_conversion_type_argument_shape_safe")
assert shape.count("proof_replay_call_conversion_builtin_generic_type_head(head, resolution_owner, resolution_owner_known, call_target, work)") == 3
single_argument_alias = shape.split("Ast::Expr.Index(head, argument, _):", 1)[1].split("Ast::Expr.IndexN(head, arguments, _):", 1)[0]
assert "field_conversion_alias_generic_application_valid[application.row]" in single_argument_alias
assert "field_conversion_alias_generic_formal_counts[application.row] != 1" in single_argument_alias
assert "if not application.found:" in single_argument_alias
assert "type_argument_shape_safe(head," in single_argument_alias
assert "type_argument_shape_safe(argument," in single_argument_alias
multi_argument_alias = shape.split("Ast::Expr.IndexN(head, arguments, _):", 1)[1]
assert "field_conversion_alias_has_formals[application.row]" in multi_argument_alias
assert "field_conversion_alias_generic_application_valid[application.row]" in multi_argument_alias
assert "arguments.count != call_target.aliases.field_conversion_alias_generic_formal_counts[application.row]" in multi_argument_alias
assert "if not application.found:" in multi_argument_alias
assert "type_argument_shape_safe(head," in multi_argument_alias

source_builtin_head = function_body("proof_source_conversion_builtin_generic_type_head")
assert "owner_target.blocks_parent" in source_builtin_head
assert "root_target.blocks_parent" in source_builtin_head
