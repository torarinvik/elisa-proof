"""Keep AST-to-kernel mirror validation behind a shared work budget."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "src/proof"


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


validation = (PROOF / "replay/certificate_ast_mirror.elisa").read_text(encoding="utf-8")
metered = function_body(validation, "proof_replay_ast_matches_kernel_with_work")
assert "source_work: mutable usize&" in validation
assert "proof_replay_summary_expr_repeat_charge_with_limit(expression, 2, source_work, PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT)" in metered
assert "proof_kernel_expression_supported(expression)" in metered
assert "proof_replay_ast_matches_kernel_checked(report, expression, root, source_work, depth)" in metered
quantifier_lookup = function_body(validation, "proof_replay_quantifier_kind_with_work")
assert "proof_report_source_work_charge(1, source_work)" in quantifier_lookup
assert "sview_len(annotation.owner)" in quantifier_lookup
assert "sview_len(annotation.name)" in quantifier_lookup
checked_matcher = function_body(validation, "proof_replay_ast_matches_kernel_checked")
assert "proof_replay_quantifier_kind_with_work(expression, report.source.source_annotations, source_work, 0)" in checked_matcher
assert "Ast::Expr.Block(statements, value, captures, block_position)" in checked_matcher
assert "Ast::Stmt.VarDecl(binder, type_expression, range_expression, binder_position)" in checked_matcher
assert "proof_replay_source_position_equal(block_position, binder_position)" in checked_matcher
assert "Ast::Stmt.VarDecl(binder, type_expression, Ast::Expr.IntLit(initializer, _), binder_position)" in checked_matcher
assert "proof_replay_quantifier_integer_type(type_expression)" in checked_matcher
assert "node.secondary_name == binder" in checked_matcher
assert "proof_replay_source_position_equal(block_position, binder_position)" in checked_matcher
assert "proof_report_source_work_charge(1, source_work)" in checked_matcher
for node_text in ("kind", "name", "secondary_name", "operator"):
    assert f"sview_len(node.{node_text})" in checked_matcher, node_text
for wrapper in ("argument_node", "entry_node"):
    assert f"sview_len({wrapper}.kind)" in checked_matcher, wrapper
assert "sview_len(argument_node.name)" in checked_matcher
assert "sview_len(expected_name)" in checked_matcher
field_matcher = function_body(validation, "proof_replay_ast_fields_match_kernel")
assert "sview_len(field_node.name)" in field_matcher
assert "sview_len(fields[index].name)" in field_matcher

# The local-counter entry point is only for the bounded runtime audit. Every report-backed
# production path must carry its existing shared work counter into the metered helper.
raw_call = re.compile(r"\bproof_replay_ast_matches_kernel\s*\(")
raw_sites: list[tuple[str, str]] = []
for path in sorted(PROOF.rglob("*.elisa")):
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if raw_call.search(line) and not re.match(r"\s*def\s+proof_replay_ast_matches_kernel\b", line):
            raw_sites.append((str(path.relative_to(ROOT)), line.strip()))
assert len(raw_sites) == 1 and raw_sites[0][0] == "src/proof/tactics/runtime_audit_api.elisa", raw_sites

for relative in (
    "src/proof/replay/certificate_validation.elisa",
    "src/proof/replay/fact_trace_validation.elisa",
    "src/proof/replay/attempt_fact_source_validation.elisa",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert "proof_replay_ast_matches_kernel_with_work(" in text, relative
    for line in text.splitlines():
        if "proof_replay_ast_matches_kernel_with_work(" in line and not re.match(
            r"\s*def\s+proof_replay_ast_matches_kernel_with_work\b", line
        ):
            assert "source_work" in line or "validation_workspace.source_scan_work_used" in line, (
                relative,
                line.strip(),
            )

for path in sorted(PROOF.rglob("*.elisa")):
    if path.name != "certificate_validation.elisa":
        assert "proof_replay_ast_matches_kernel_unmetered(" not in path.read_text(encoding="utf-8"), path

print("AST/kernel mirror checks: production call sites share the replay work budget")
