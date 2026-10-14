"""Guard recursive return conversion and conditional prepass against unmetered scans."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
contracts = (ROOT / "src/proof/check/returns/contracts.elisa").read_text(encoding="utf-8")
conversion = (ROOT / "src/proof/check/returns/bounded_conversion.elisa").read_text(encoding="utf-8")
conditional = (ROOT / "src/proof/check/returns/conditional_values.elisa").read_text(encoding="utf-8")
caller = (ROOT / "src/proof/check/statement_checks.elisa").read_text(encoding="utf-8")
loops = (ROOT / "src/proof/check/returns/loops.elisa").read_text(encoding="utf-8")
contract_helpers = (ROOT / "src/proof/check/returns/contracts_helpers.elisa").read_text(encoding="utf-8")
catch_returns = (ROOT / "src/proof/check/statement_catch_returns.elisa").read_text(encoding="utf-8")

assert "proof_return_bounded_u8_conversion_with_work" in contracts
assert "proof_return_call_is_conversion_with_work" in contracts
assert "not conversion_complete or conversion_exhausted or not shared_conversion_work_ok" in contracts
assert "proof_expr_calls_are_conversions" not in contracts
assert '"bounded-conversion-work"' in contracts
assert "remaining_return_source_work" in contracts
assert "conversion_budget_start" in contracts
assert "proof_linear_safety_work_charge_scaled(budget, exhausted, sview_len(target), PROOF_FACT_NUMERIC_CAST_TARGET_COUNT + 10)" in conversion
assert "proof_runtime_numeric_conversion(callee, arguments.count, functions)" in conversion
assert 'return (true, false) if field == ""' in conversion
assert "Ast::Expr.If(condition, then_expression, else_expression, _)" in conversion

assert "proof_expr_calls_are_conversions" not in conditional
assert "proof_conditional_calls_are_conversions_with_work" in conditional
assert "proof_conditional_arm_indexes_with_work" in conditional
assert "proof_is_type_cast_index(object)" not in conditional
assert "proof_conditional_type_cast_index_with_work" in conditional
assert "proof_conditional_strip_parens_with_work" in conditional
assert "proof_linear_safety_work_charge(budget, exhausted, 1)" in conditional
assert "conditional_allowance" in caller
assert "conditional_exhausted or not conditional_shared_work_ok" in caller
assert "proof_split_conditional_value(body, functions, &conditional_work, &conditional_exhausted)" in caller
substitution_budget = (ROOT / "src/proof/check/lemma_application_budget.elisa").read_text(encoding="utf-8")
rewrite_budget = substitution_budget
runtime_stability = (ROOT / "src/proof/check/contracts_and_frames.elisa").read_text(encoding="utf-8")
assert "def proof_return_expression_scan_charge" in substitution_budget
assert "proof_replay_summary_expr_repeat_charge_with_limit(expression, 1, &scan_work, PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT)" in substitution_budget
assert "proof_purity_work_charge(scan_work, &work)" in substitution_budget
assert "proof_return_expression_scan_charge(expression, report, name, line)" in runtime_stability
assert "proof_source_expression_has_overloaded_operator(expression, operator_mask, 0)" in runtime_stability
assert "proof_expr_has_call(source_expression)" in runtime_stability
stability_start = runtime_stability.index("def proof_runtime_fact_is_stable")
stability_end = runtime_stability.index("def ", stability_start + 5)
stability = runtime_stability[stability_start:stability_end]
assert stability.count("proof_return_expression_scan_charge(source_expression, report, name, line)") == 2
assert stability.count("proof_return_expression_scan_charge(expression, report, name, line)") == 6
assert "proof_frame_expression_has_overloaded_operator_with_work(condition, report.source.source_primitive_operator_mask, report, name, position.line)" in contracts
assert "proof_frame_expression_has_overloaded_operator_with_work(condition, report.source.source_primitive_operator_mask, report, name, position.line)" in loops
assert "if proof_frame_source_work_stop(report, name, position.line):" in loops
assert "proof_source_expression_has_overloaded_operator(condition, report.source.source_primitive_operator_mask, 0)" not in loops
generic_stmt = contracts.split("generic_expression_has_call: bool =", 1)[1].split("if expression_has_unmodeled_operator:", 1)[0]
assert "proof_frame_expression_has_call_with_work(expression, report, name, position.line)" in generic_stmt
assert generic_stmt.count("proof_expr_has_call(expression)") == 0
assert "if proof_frame_source_work_stop(report, name, position.line):" in generic_stmt
return_stmt = contracts.split("prepared_return: (ready: bool, expression: Ast::Expr) = proof_return_substitution_prepare(returned, names, values, report, name, position.line)", 1)[1].split("returned_has_unmodeled_operator:", 1)[0]
assert "if not prepared_return.ready:" in return_stmt
assert "return_value: mutable Ast::Expr = prepared_return.expression" in return_stmt
assert "returned_has_call: bool = proof_frame_expression_has_call_with_work(returned, report, name, position.line)" in return_stmt
assert "return_value_has_call: mutable bool = proof_frame_expression_has_call_with_work(return_value, report, name, position.line)" in return_stmt
assert "proof_expr_has_call(returned)" not in return_stmt
assert "proof_expr_has_call(return_value)" not in return_stmt
assert return_stmt.count("if proof_frame_source_work_stop(report, name, position.line):") == 1
post_call_stmt = contracts.split("post_call_return: (ready: bool, expression: Ast::Expr) =", 1)[1].split("return_value <- proof_rewrite_pure_call_summaries", 1)[0]
assert "proof_return_substitution_prepare(returned, names, values, report, name, position.line)" in post_call_stmt
assert "if not post_call_return.ready:" in post_call_stmt
assert "proof_expr_has_call(goal)" not in contracts
assert "current_goal_has_call: bool = proof_frame_expression_has_call_with_work(current_goal, report, name, position.line)" in contracts
assert "goal_has_call: mutable bool = proof_frame_expression_has_call_with_work(goal, report, name, position.line)" in contracts
assert "void_goal_has_call: bool = proof_frame_expression_has_call_with_work(goal, report, name, position.line)" in contracts
assert "current_goal_has_call: bool) -> bool" in contract_helpers
assert "proof_expr_has_call(current_goal)" not in contract_helpers
assert "def proof_return_pure_call_rewrite_reserve" in rewrite_budget
for formula_part in ("facts.count, expression_cost * 24", "facts_cost, 30", "facts_cost, expression_cost * 8", "PROOF_TERM_OCCURS_DEPTH_LIMIT + 1", "PROOF_PURE_CALL_REWRITE_DEPTH_LIMIT", "proof_purity_work_charge(total_cost, &work)"):
    assert formula_part in rewrite_budget
reserve_start = rewrite_budget.index("def proof_return_pure_call_rewrite_reserve")
reserve_end = rewrite_budget.index("def proof_return_expression_scan_charge", reserve_start)
reserve = rewrite_budget[reserve_start:reserve_end]
assert "proof_replay_summary_expr_cost_with_limit(expression" in reserve
assert "proof_replay_summary_expr_cost_with_limit(fact" in reserve
assert reserve.count("proof_return_rewrite_bound_add_product(") == 5
assert "available / depth < combined_cost" in reserve
assert "per_depth_allowance: usize = (available / depth - combined_cost) / combined_cost" in reserve
assert "report.analysis_1.budgets.return_source_work <- work.used" in reserve
assert "report.analysis_1.budgets.return_source_reported <- work.reported" in reserve
assert contracts.count("proof_return_pure_call_rewrite_reserve(") == 3
assert catch_returns.count("proof_return_pure_call_rewrite_reserve(") == 2
print("return source work: conversion and conditional prepasses share the bounded per-function meter")
