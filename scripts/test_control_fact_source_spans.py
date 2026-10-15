"""Require recursive parser-span matching for source-bound control facts."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
control = (ROOT / "src/proof/replay/boundary_control_sources.elisa").read_text(encoding="utf-8")
position_source = (ROOT / "src/proof/replay/attempt_fact_source_validation.elisa").read_text(encoding="utf-8")


def body(source: str, name: str) -> str:
    lines = source.splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\s*def {re.escape(name)}\b", line))
    indent = len(lines[start]) - len(lines[start].lstrip())
    result = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        result.append(line)
    return "\n".join(result)


source_equal = body(control, "proof_replay_control_expr_source_equal_with_work")
recursive_positions = "proof_replay_trace_expression_positions_equal_with_work(left, right, 0, work, work_limit)"
assert source_equal.index("proof_replay_summary_expr_equal_with_limit") < source_equal.index(recursive_positions)
assert source_equal.index(recursive_positions) < source_equal.index("match left:")
# Root identifier substitution is the one supported span exception, because the checker
# substitutes a declaration-site identifier for the source use-site identifier.
assert "Ast::Expr.Ident(name, _)" in source_equal and "Ast::Expr.Ident(other, _)" in source_equal
assert "return name == other" in source_equal
assert "proof_replay_control_expr_position_equal(" not in control
assert "proof_replay_control_expr_source_equal(" not in control
loop_sources = (ROOT / "src/proof/replay/boundary_loop_fact_sources.elisa").read_text(encoding="utf-8")
branch_sources = (ROOT / "src/proof/replay/boundary_branch_fact_sources.elisa").read_text(encoding="utf-8")
assert "proof_replay_trace_expression_positions_equal_with_work(trace.expression, lower, 0, source_work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in loop_sources
assert "proof_replay_trace_expression_positions_equal_with_work(trace.expression, upper, 0, source_work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in loop_sources
assert "proof_replay_trace_expression_positions_equal_with_work(trace.expression, expected_exit, 0, source_work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in loop_sources
assert "proof_replay_trace_expression_positions_equal_with_work(trace.expression, negated, 0, work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in branch_sources
assert "proof_replay_trace_expression_positions_equal_with_work(trace.expression, rejected, 0, work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in branch_sources
assert "proof_replay_control_expr_position_equal(" not in loop_sources
assert "proof_replay_control_expr_position_equal(" not in branch_sources

positions = body(position_source, "proof_replay_trace_expression_positions_equal_with_work")
assert "depth >= PROOF_REPLAY_AST_DEPTH_LIMIT" in positions
assert "proof_replay_position_work_charge(work, 6, work_limit)" in positions
assert positions.index("proof_replay_position_work_charge(work, 6, work_limit)") < positions.index("Ast::expr_pos(left)")
for constructor in (
    "Ast::Expr.Unary", "Ast::Expr.Binary", "Ast::Expr.If", "Ast::Expr.Call",
    "Ast::Expr.Field", "Ast::Expr.Scope", "Ast::Expr.Index", "Ast::Expr.Construct",
    "Ast::Expr.Tuple", "Ast::Expr.Array", "Ast::Expr.Block",
):
    assert constructor in positions, constructor
assert "Ast::Stmt.VarDecl" in positions
assert "_:\n                    return false" in positions

print("control-flow source binding: nested spans are matched under a shared bounded meter")
