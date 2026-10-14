"""Guard generic type alias applications through source type normalization."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/proof/check/source_conversion_alias_resolution.elisa"


def function_body(name: str) -> str:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
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
