"""Bound quantified call-summary expansion and its repeated AST copies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/check/quantified_call_summaries.elisa").read_text(encoding="utf-8")

assert "PROOF_QUANTIFIED_CALL_SOURCE_WORK_LIMIT: usize = PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT" in source
assert "source_work: mutable usize = report.source_types.source_effect_index.work.implicit_effect_work" in source
assert "report.source_types.source_effect_index.work.implicit_effect_work <- source_work" in source
assert "proof_quantified_call_source_charge(1, source_work)" in source
assert "Ast::Expr.Field(object, _, _):\n                    # The pure-call witness builder descends through field receivers." in source
field_branch = source.split("Ast::Expr.Field(object, _, _):", 1)[1].split("Ast::Expr.Binary(left, operator, right, _):", 1)[0]
assert "proof_add_quantified_call_summaries_depth(object, facts, functions" in field_branch
assert "proof_quantified_call_source_expression_charge(predicate, 1, source_work)" in source
assert "proof_quantified_call_source_copy_facts(facts, source_work)" in source
assert "PROOF_QUANTIFIED_CALL_WITNESS_SCAN_MULTIPLIER" not in source
assert "proof_quantified_call_source_witness_reserve" not in source
assert "proof_replay_summary_expr_repeat_charge_with_limit(fact, 1, &source_work, PROOF_QUANTIFIED_CALL_SOURCE_WORK_LIMIT)" in source
assert "proof_index_call_result(expression, &before, functions, annotations, facts, report, owner, true)" in source
assert "proof_contract_calls_are_pure_with_source_work_limit(expression, functions, source_work, PROOF_QUANTIFIED_CALL_SOURCE_WORK_LIMIT)" in source
assert "not instantiated or not proof_contract_calls_are_pure(expression, functions)" not in source
assert "proof_quantifier_kind(" not in source
assert "proof_logical_contract_supported(" not in source
assert "proof_contract_calls_are_pure(" not in source
assert "solver_work: mutable usize = 0" in source
assert "solver_exhausted: mutable bool = false" in source
assert source.count("proof_goal_with_operator_mask_and_work(facts,") == 2
assert "proof_goal_with_operator_mask(facts," not in source
assert "or solver_exhausted" in source
assert "if source_work > PROOF_QUANTIFIED_CALL_SOURCE_WORK_LIMIT:" in source
assert "quantified-call-source-work" in source
call_branch = source.split("Ast::Expr.Call(_, arguments, _, position):", 1)[1]
assert call_branch.index("report.source_types.source_effect_index.work.implicit_effect_work <- source_work") < call_branch.index("proof_add_pure_call_witnesses(expression, facts, functions, report, position.line, owner, 0)")
assert call_branch.index("source_work <- report.source_types.source_effect_index.work.implicit_effect_work") > call_branch.index("proof_add_pure_call_witnesses(expression, facts, functions, report, position.line, owner, 0)")
assert "if not proof_add_pure_call_witnesses(expression, facts, functions, report, position.line, owner, 0):" in call_branch
assert "proof_contract_calls_are_pure_with_source_work_limit(expression, functions, source_work, PROOF_QUANTIFIED_CALL_SOURCE_WORK_LIMIT)" in source
print("quantified call summaries: recursive visits, solver probes, fact copies, and witness scans share bounded work")
