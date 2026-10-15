"""Build the scalar fact index once per pure-call argument group."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/check/operator_witnesses.elisa").read_text(encoding="utf-8")
wrapper = source.split("def proof_add_pure_call_witnesses(", 1)[1].split("def proof_add_pure_call_witnesses_with_work(", 1)[0]
worker = source.split("def proof_add_pure_call_witnesses_with_work(", 1)[1].split("# Zero means a non-unsigned type", 1)[0]
call_branch = worker.split("Ast::Expr.Call(callee, arguments, _, position):", 1)[1].split("Ast::Expr.Field(object, field, position):", 1)[0]
assert "proof_add_pure_call_witnesses_with_work(expression, facts" in wrapper
assert "report.analysis_1.budgets.frame_call_source_work <- budget" in wrapper
assert "proof_frame_source_work_report_exhaustion" in wrapper
assert "proof_add_widening_cast_witnesses_with_work(expression, callee, arguments.count, facts, functions, report, line, owner, position, budget, exhausted)" in call_branch
assert "proof_add_widening_cast_witnesses(expression, callee" not in call_branch
assert "proof_contract_calls_are_pure_with_source_work(expression, functions, true, budget)" in call_branch
assert "source_work <- report.source_types.source_effect_index.work.implicit_effect_work" in call_branch
assert "source_work >= PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT or not return_markers.complete" in call_branch
assert "return if return_markers.reference" in call_branch
tuple_source = (ROOT / "src/proof/check/tuple_label_index.elisa").read_text(encoding="utf-8")
tuple_worker = tuple_source.split("def proof_add_tuple_field_call_witnesses_with_work(", 1)[1].split("# A named-tuple call result", 1)[0]
assert "budget: mutable usize&, exhausted: mutable bool&" in tuple_worker.splitlines()[0]
assert "proof_contract_calls_are_pure_with_source_work(object, functions, true, budget)" in tuple_worker
assert "proof_scalar_witness_markers_with_work(facts, false, budget, exhausted)" in tuple_worker
assert "proof_linear_safety_scalar_witness_with_work(argument, marker_result.witnesses, marker_scale.scale, budget, exhausted)" in tuple_worker
assert "proof_value_binding_argument_with_work(argument, report, 0, budget, exhausted)" in tuple_worker
assert "proof_add_tuple_label_witnesses_with_work(object, called, field, true" in tuple_worker
assert "proof_add_tuple_field_call_witnesses_with_work(object, field, facts, functions, report, line, owner, position, budget, exhausted)" in source
tuple_witness_worker = tuple_source.split("def proof_add_tuple_label_witnesses_with_work(", 1)[1]
fact_work = (ROOT / "src/proof/check/pure_call_witness_work.elisa").read_text(encoding="utf-8")
fact_seen = fact_work.split("def proof_pure_call_fact_seen_with_work(", 1)[1].split("def proof_pure_call_add_scalar_witness_with_work(", 1)[0]
assert "proof_replay_expr_equal_depth(existing, expression, 0)" in fact_seen
assert "proof_linear_search_expr_equal_with_work" not in fact_seen
assert "proof_pure_call_add_scalar_witness_with_work(facts, report, scalar_marker" in tuple_witness_worker
assert "proof_pure_call_add_type_fact_with_work(facts, report, signed_upper" in tuple_witness_worker
assert "labeled_field <- true if label == field" in tuple_witness_worker
assert "for index in 0..<count" in tuple_witness_worker
assert "proof_frame_source_work_report_exhaustion(report, owner, line, \"tuple-call-witness-work\"" in tuple_source
assert call_branch.count("proof_scalar_witness_markers_with_work(facts, false, budget, exhausted)") == 1
assert "proof_linear_safety_scalar_witness_with_work(argument, scalar_markers, marker_scale.scale, budget, exhausted)" in call_branch
assert "proof_value_binding_argument_with_work(argument, report, 0, budget, exhausted)" in call_branch
assert "proof_scalar_term_witnessed(argument, facts, 0)" not in call_branch
argument_loops = [i for i in range(len(call_branch)) if call_branch.startswith("for argument in arguments", i)]
assert len(argument_loops) == 2
assert argument_loops[0] < call_branch.index("scalar_markers_result") < argument_loops[1]
assert "return if not scalar_markers_result.complete or exhausted" in call_branch
binding_source = (ROOT / "src/proof/check/enum_value_types.elisa").read_text(encoding="utf-8")
binding_worker = binding_source.split("def proof_value_binding_argument_with_work(", 1)[1].split("# The declared payload types", 1)[0]
assert "proof_linear_safety_work_charge(budget, exhausted" in binding_worker
assert "report.aliases.value_binding_names" in binding_worker
assert "report.aliases.aliased_names" in binding_worker
assert "sview_len(owned)" in binding_worker and "sview_len(existing)" in binding_worker
deterministic_source = (ROOT / "src/proof/check/deterministic_call_witness_work.elisa").read_text(encoding="utf-8")
deterministic_worker = deterministic_source.split("def proof_add_deterministic_call_witness_with_work(", 1)[1]
assert deterministic_worker.index("Ast::Expr.Call(_, _, _, _):") < deterministic_worker.index("for fact in facts")
assert "if not equal.complete:" in deterministic_source and "exhausted <- true" in deterministic_source
assert "proof_deterministic_term_occurs_with_work(marker.term, expression" in deterministic_worker
assert "proof_deterministic_chain_arithmetic_with_work(expression, facts, links" in deterministic_worker
assert "proof_scalar_witness_markers_with_work(facts, true, budget, exhausted)" in deterministic_worker
assert "proof_linear_safety_scalar_witness_with_work(argument, markers_result.witnesses, marker_scale.scale, budget, exhausted)" in deterministic_worker
assert "proof_value_binding_argument_with_work(argument, report, 0, budget, exhausted)" in deterministic_worker
assert "proof_shared_fixed_parameter_with_work(report, caller_names, caller_parameters" in deterministic_worker
assert "proof_scalar_term_witnessed(argument, facts, 0)" not in deterministic_worker
linear_source = (ROOT / "src/proof/linear/producer_scalar_comparison.elisa").read_text(encoding="utf-8")
linear_scalar_witness = linear_source.split("def proof_linear_search_scalar_term_witnessed(", 1)[1].split("\n        def ", 1)[0]
integrated_source = (ROOT / "src/proof/linear/bounds_and_markers_integrated_helpers.elisa").read_text(encoding="utf-8")
integrated_scalar_witness = integrated_source.split("def proof_linear_safety_scalar_witness_with_work(", 1)[1].split("\n        def ", 1)[0]
assert "proof_linear_search_scalar_term_witnessed(expression, markers, 0, &budget, PROOF_LINEAR_SAFETY_WORK_LIMIT, true)" in integrated_scalar_witness
assert "not witnessed.complete or exhausted" in integrated_scalar_witness
assert "proof_linear_safety_expr_cost_with_work(expression" not in integrated_scalar_witness
assert "proof_linear_safety_charge_cross_with_work" not in integrated_scalar_witness
assert "proof_linear_search_expr_equal_with_work(scalar_term, expression" in linear_scalar_witness
owner_source = (ROOT / "src/proof/check/function_contracts_and_frames.elisa").read_text(encoding="utf-8")
owner_wrapper = owner_source.split("def proof_add_deterministic_call_witness(", 1)[1].split("def ", 1)[0]
assert "proof_frame_source_work_report_exhaustion" in owner_wrapper
assert "budget >= PROOF_LINEAR_SAFETY_WORK_LIMIT" in owner_wrapper
assert 'include "./check/deterministic_call_witness_work.elisa"' in (ROOT / "src/proof/check.elisa").read_text(encoding="utf-8")

consumers = {
    "check/function_checks.elisa": (
        "witness_complete: bool = not goal_has_call or proof_add_pure_call_witnesses(",
        "proven: bool = witness_complete and",
    ),
    "check/returns/contracts.elisa": (
        "witness_complete: bool = proof_add_pure_call_witnesses(",
        "proven <- witness_complete and",
    ),
    "check/statement_catch_returns.elisa": (
        "witness_complete: bool = not goal_has_call or proof_add_pure_call_witnesses(",
        "proven: bool = witness_complete and",
    ),
    "check/function_contracts_and_frames.elisa": (
        "return false if not proof_add_pure_call_witnesses(",
        "proof_add_deterministic_call_witness(",
    ),
    "check/unfolded_summaries.elisa": (
        "return if not proof_add_pure_call_witnesses(",
    ),
    "check/quantified_call_summaries.elisa": (
        "if not proof_add_pure_call_witnesses(",
        "source_work <- PROOF_QUANTIFIED_CALL_SOURCE_WORK_LIMIT + 1",
    ),
}
for relative_path, expected in consumers.items():
    consumer = (ROOT / "src/proof" / relative_path).read_text(encoding="utf-8")
    for fragment in expected:
        assert fragment in consumer, f"{relative_path} must propagate witness exhaustion: {fragment}"
print("pure-call witnesses: bounded marker snapshot is reused for all call arguments")
