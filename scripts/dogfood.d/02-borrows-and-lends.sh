# shellcheck shell=bash
# Part 2 of scripts/dogfood.sh; sourced in order by it, never run alone.
run_probe rejected_unsigned_overflow_goal examples/rejected_unsigned_overflow_goal.elisa 1
run_probe borrow_multi_indexed_places examples/borrow_multi_indexed_places.elisa 0
run_probe rejected_borrow_multi_index_alias examples/rejected_borrow_multi_index_alias.elisa 1
run_probe borrow_dynamic_whole_root examples/borrow_dynamic_whole_root.elisa 0
run_probe rejected_borrow_dynamic_alias examples/rejected_borrow_dynamic_alias.elisa 1
run_probe borrow_dynamic_multi_whole_root examples/borrow_dynamic_multi_whole_root.elisa 0
run_probe rejected_borrow_dynamic_multi_alias examples/rejected_borrow_dynamic_multi_alias.elisa 1
run_probe borrow_symbolic_disjoint examples/borrow_symbolic_disjoint.elisa 0
run_probe rejected_borrow_symbolic_alias examples/rejected_borrow_symbolic_alias.elisa 1
run_probe for_invariant examples/for_invariant.elisa 0
run_probe for_loop_control_invariant examples/for_loop_control_invariant.elisa 0
run_probe region_allocation examples/region_allocation.elisa 0
run_probe region_scalar_copy examples/region_scalar_copy.elisa 0
run_probe region_statement examples/region_statement.elisa 0
run_probe region_auto_close examples/region_auto_close.elisa 0
run_probe region_generic_allocation examples/region_generic_allocation.elisa 0
run_probe rejected_region_generic_unmapped examples/rejected_region_generic_unmapped.elisa 1
run_probe rejected_region_use_after_destroy examples/rejected_region_use_after_destroy.elisa 1
run_probe rejected_region_destroy_nested_without_binding examples/rejected_region_destroy_nested_without_binding.elisa 1
run_probe rejected_region_duplicate_mutable_alias examples/rejected_region_duplicate_mutable_alias.elisa 1
run_probe rejected_region_assign_duplicate_owner examples/rejected_region_assign_duplicate_owner.elisa 1
run_probe rejected_region_bind_mutable_external examples/rejected_region_bind_mutable_external.elisa 1
run_probe rejected_region_call_result_duplicate_owner examples/rejected_region_call_result_duplicate_owner.elisa 1
run_probe rejected_for_invariant examples/rejected_for_invariant.elisa 1
run_probe rejected_for_invariant_scope examples/rejected_for_invariant_scope.elisa 1
run_probe loop_accumulator examples/loop_accumulator.elisa 0
run_probe rejected_loop_accumulator examples/rejected_loop_accumulator.elisa 1
run_probe fixed_array_fields examples/fixed_array_fields.elisa 0
run_probe rejected_fixed_array_fields examples/rejected_fixed_array_fields.elisa 1
run_probe nested_call_kept_values examples/nested_call_kept_values.elisa 0
run_probe rejected_nested_call_kept_values examples/rejected_nested_call_kept_values.elisa 1
run_probe literal_index examples/literal_index.elisa 0
run_probe rejected_literal_index examples/rejected_literal_index.elisa 1
run_probe disjunctive_goals examples/disjunctive_goals.elisa 0
run_probe rejected_disjunctive_goals examples/rejected_disjunctive_goals.elisa 1
run_probe leaving_branch_join examples/leaving_branch_join.elisa 0
run_probe rejected_leaving_branch_join examples/rejected_leaving_branch_join.elisa 1
run_probe pass_statement examples/pass_statement.elisa 0
run_probe rejected_pass_statement examples/rejected_pass_statement.elisa 1
run_probe counting_loop_measure examples/counting_loop_measure.elisa 0
run_probe rejected_counting_loop_measure examples/rejected_counting_loop_measure.elisa 1
run_probe congruence examples/congruence.elisa 0
run_probe rejected_congruence examples/rejected_congruence.elisa 1
run_probe rejected_reflexivity examples/rejected_reflexivity.elisa 1
run_probe expression_witness examples/expression_witness.elisa 0
run_probe call_stable_facts examples/call_stable_facts.elisa 0
run_probe rejected_call_stable_facts examples/rejected_call_stable_facts.elisa 1
run_probe rejected_nested_shared_extent_global examples/rejected_nested_shared_extent_global.elisa 1
run_probe rejected_borrowed_view_call_stability examples/rejected_borrowed_view_call_stability.elisa 1
run_probe shared_borrow_calls examples/shared_borrow_calls.elisa 0
run_probe rejected_shared_borrow_calls examples/rejected_shared_borrow_calls.elisa 1
run_probe writable_lend_calls examples/writable_lend_calls.elisa 0
run_probe rejected_writable_lend_calls examples/rejected_writable_lend_calls.elisa 1
run_probe region_lend_calls examples/region_lend_calls.elisa 0
run_probe rejected_region_lend_calls examples/rejected_region_lend_calls.elisa 1
run_probe region_call_summary examples/region_call_summary.elisa 0
run_probe condition_call_positions examples/condition_call_positions.elisa 0
run_probe rejected_condition_call_positions examples/rejected_condition_call_positions.elisa 1
run_probe product_sign examples/product_sign.elisa 0
run_probe rejected_product_sign examples/rejected_product_sign.elisa 1
run_probe frame_lifetime examples/frame_lifetime.elisa 0
run_probe rejected_frame_lifetime examples/rejected_frame_lifetime.elisa 1
run_probe unnamed_lifetime_lend examples/unnamed_lifetime_lend.elisa 1
run_probe rejected_unnamed_lifetime_lend examples/rejected_unnamed_lifetime_lend.elisa 1
run_probe captured_block examples/captured_block.elisa 0
run_probe rejected_captured_block examples/rejected_captured_block.elisa 1
run_probe uncaptured_binding examples/uncaptured_binding.elisa 0
run_probe rejected_uncaptured_binding examples/rejected_uncaptured_binding.elisa 1
run_probe rejected_uncaptured_block_write examples/rejected_uncaptured_block_write.elisa 1
run_probe loop_element_extent examples/loop_element_extent.elisa 1
run_probe rejected_loop_element_extent examples/rejected_loop_element_extent.elisa 1
run_probe comparison_chain_equality examples/comparison_chain_equality.elisa 0
run_probe rejected_comparison_chain_equality examples/rejected_comparison_chain_equality.elisa 1
run_probe region_extent_contract examples/region_extent_contract.elisa 0
run_probe rejected_region_extent_contract examples/rejected_region_extent_contract.elisa 1
run_probe region_statement_call examples/region_statement_call.elisa 0
run_probe rejected_region_statement_call examples/rejected_region_statement_call.elisa 1
run_probe region_lifetime_free_callee examples/region_lifetime_free_callee.elisa 0
run_probe rejected_region_lifetime_free_callee examples/rejected_region_lifetime_free_callee.elisa 1
run_probe short_circuit_guard examples/short_circuit_guard.elisa 0
run_probe rejected_short_circuit_guard examples/rejected_short_circuit_guard.elisa 1
run_probe call_guard_summaries examples/call_guard_summaries.elisa 0
run_probe rejected_call_guard_summaries examples/rejected_call_guard_summaries.elisa 1
run_probe loop_binder_call_requires examples/loop_binder_call_requires.elisa 0
run_probe rejected_loop_binder_call_requires examples/rejected_loop_binder_call_requires.elisa 1
run_probe disequality_bounds examples/disequality_bounds.elisa 0
run_probe rejected_disequality_bounds examples/rejected_disequality_bounds.elisa 1
run_probe conditional_equality_split examples/conditional_equality_split.elisa 0
run_probe rejected_conditional_equality_split examples/rejected_conditional_equality_split.elisa 1
run_probe place_aliases examples/place_aliases.elisa 0
run_probe rejected_place_aliases examples/rejected_place_aliases.elisa 1
run_probe field_places examples/field_places.elisa 0
run_probe rejected_field_places examples/rejected_field_places.elisa 1
run_probe guarded_differences examples/guarded_differences.elisa 0
run_probe typed_wide_constants examples/typed_wide_constants.elisa 0
run_probe rejected_typed_wide_constants examples/rejected_typed_wide_constants.elisa 1
run_probe complemented_else_arms examples/complemented_else_arms.elisa 0
run_probe rejected_complemented_else_arms examples/rejected_complemented_else_arms.elisa 1
run_probe rejected_guarded_differences examples/rejected_guarded_differences.elisa 1
run_probe literal_widths examples/literal_widths.elisa 0
run_probe rejected_literal_widths examples/rejected_literal_widths.elisa 1
run_probe shared_fixed_borrows examples/shared_fixed_borrows.elisa 0
run_probe rejected_shared_fixed_borrows examples/rejected_shared_fixed_borrows.elisa 1
run_probe rejected_shared_fixed_global examples/rejected_shared_fixed_global.elisa 1
run_probe bound_call_summaries examples/bound_call_summaries.elisa 0
run_probe rejected_bound_call_summaries examples/rejected_bound_call_summaries.elisa 1
run_probe value_call_arguments examples/value_call_arguments.elisa 0
run_probe rejected_value_call_arguments examples/rejected_value_call_arguments.elisa 1
run_probe call_result_places examples/call_result_places.elisa 0
run_probe rejected_call_result_places examples/rejected_call_result_places.elisa 1
run_probe rebind_join examples/rebind_join.elisa 0
run_probe rejected_rebind_join examples/rejected_rebind_join.elisa 1
run_probe conditional_conversions examples/conditional_conversions.elisa 0
run_probe rejected_conditional_conversions examples/rejected_conditional_conversions.elisa 1
run_probe conditional_call_arms examples/conditional_call_arms.elisa 0
run_probe rejected_conditional_call_arms examples/rejected_conditional_call_arms.elisa 1
run_probe guarded_conditional_arms examples/guarded_conditional_arms.elisa 0
run_probe rejected_guarded_conditional_arms examples/rejected_guarded_conditional_arms.elisa 1
run_probe captured_block_exit examples/captured_block_exit.elisa 0
run_probe rejected_captured_block_exit examples/rejected_captured_block_exit.elisa 1
run_probe global_constant_loop_exit examples/global_constant_loop_exit.elisa 0
run_probe rejected_global_constant_loop_exit examples/rejected_global_constant_loop_exit.elisa 1
run_probe branch_join examples/branch_join.elisa 0
run_probe rejected_branch_join examples/rejected_branch_join.elisa 1
run_probe loop_state_joins examples/loop_state_joins.elisa 0
run_probe rejected_loop_state_joins examples/rejected_loop_state_joins.elisa 1
run_probe bound_propagation examples/bound_propagation.elisa 0
run_probe rejected_bound_propagation examples/rejected_bound_propagation.elisa 1
run_probe strict_shift examples/strict_shift.elisa 0
run_probe rejected_strict_shift examples/rejected_strict_shift.elisa 1
run_probe sum_bound examples/sum_bound.elisa 0
run_probe rejected_sum_bound examples/rejected_sum_bound.elisa 1
run_probe replay_safety_context examples/replay_safety_context.elisa 0
run_probe settled_operand examples/settled_operand.elisa 0
run_probe rejected_settled_operand examples/rejected_settled_operand.elisa 1
run_probe negated_guard_order examples/negated_guard_order.elisa 0
run_probe rejected_negated_guard_order examples/rejected_negated_guard_order.elisa 1
run_probe place_order examples/place_order.elisa 0
run_probe rejected_place_order examples/rejected_place_order.elisa 1
run_probe unsigned_place examples/unsigned_place.elisa 0
run_probe rejected_unsigned_place examples/rejected_unsigned_place.elisa 1
run_probe literal_extent examples/literal_extent.elisa 0
run_probe rejected_literal_extent examples/rejected_literal_extent.elisa 1
run_probe owned_extent examples/owned_extent.elisa 0
run_probe rejected_owned_extent examples/rejected_owned_extent.elisa 1
run_probe captured_scalar examples/captured_scalar.elisa 0
run_probe rejected_captured_scalar examples/rejected_captured_scalar.elisa 1
run_probe no_op_statement examples/no_op_statement.elisa 0
run_probe rejected_no_op_statement examples/rejected_no_op_statement.elisa 1
run_probe nested_call_value examples/nested_call_value.elisa 0
run_probe rejected_nested_call_value examples/rejected_nested_call_value.elisa 1
run_probe collection_builtin examples/collection_builtin.elisa 0
run_probe rejected_collection_builtin examples/rejected_collection_builtin.elisa 1
run_probe rejected_shadowed_collection_builtin examples/rejected_shadowed_collection_builtin.elisa 1
run_probe bound_loop_condition examples/bound_loop_condition.elisa 1
run_probe rejected_bound_loop_condition examples/rejected_bound_loop_condition.elisa 1
run_probe block_statement_region examples/block_statement_region.elisa 0
run_probe rejected_block_statement_region examples/rejected_block_statement_region.elisa 1
run_probe forward_scan examples/forward_scan.elisa 0
run_probe rejected_forward_scan examples/rejected_forward_scan.elisa 1
run_probe nested_extent examples/nested_extent.elisa 0
run_probe rejected_nested_extent examples/rejected_nested_extent.elisa 1
run_probe value_root_field examples/value_root_field.elisa 0
run_probe rejected_value_root_field examples/rejected_value_root_field.elisa 1
run_probe shared_extent_loop examples/shared_extent_loop.elisa 0
run_probe rejected_shared_extent_loop examples/rejected_shared_extent_loop.elisa 1
run_probe replay_literal_facts examples/replay_literal_facts.elisa 0
run_probe rejected_replay_literal_facts examples/rejected_replay_literal_facts.elisa 1
run_probe unsigned_nonnegative_sum examples/unsigned_nonnegative_sum.elisa 0
run_probe rejected_unsigned_nonnegative_sum examples/rejected_unsigned_nonnegative_sum.elisa 1
run_probe negated_guard_range examples/negated_guard_range.elisa 0
run_probe rejected_negated_guard_range examples/rejected_negated_guard_range.elisa 1
run_probe confined_lend_extent examples/confined_lend_extent.elisa 0
run_probe rejected_confined_lend_extent examples/rejected_confined_lend_extent.elisa 1
run_probe confined_lend_across_calls examples/confined_lend_across_calls.elisa 0
run_probe rejected_confined_lend_across_calls examples/rejected_confined_lend_across_calls.elisa 1
run_probe aggregate_local_symbol examples/aggregate_local_symbol.elisa 0
run_probe rejected_aggregate_local_symbol examples/rejected_aggregate_local_symbol.elisa 1
run_probe collection_builtin_extent examples/collection_builtin_extent.elisa 0
run_probe rejected_collection_builtin_extent examples/rejected_collection_builtin_extent.elisa 1
run_probe loop_counter_invariant examples/loop_counter_invariant.elisa 0
run_probe rejected_loop_counter_invariant examples/rejected_loop_counter_invariant.elisa 1
run_probe call_boundary_binding examples/call_boundary_binding.elisa 0
run_probe rejected_call_boundary_binding examples/rejected_call_boundary_binding.elisa 1
run_probe short_circuit_call examples/short_circuit_call.elisa 0
run_probe rejected_short_circuit_call examples/rejected_short_circuit_call.elisa 1
run_probe branch_conjunct_placeholder examples/branch_conjunct_placeholder.elisa 1
run_probe rejected_branch_conjunct_placeholder examples/rejected_branch_conjunct_placeholder.elisa 1
run_probe loop_entry_state examples/loop_entry_state.elisa 1
run_probe rejected_loop_entry_state examples/rejected_loop_entry_state.elisa 1
run_probe loop_condition_facts examples/loop_condition_facts.elisa 1
run_probe rejected_loop_condition_facts examples/rejected_loop_condition_facts.elisa 1
run_probe rejected_shared_extent_global examples/rejected_shared_extent_global.elisa 1
run_probe comparison_chain examples/comparison_chain.elisa 0
run_probe rejected_comparison_chain examples/rejected_comparison_chain.elisa 1
run_probe widened_state_summary examples/widened_state_summary.elisa 1
run_probe rejected_widened_state_summary examples/rejected_widened_state_summary.elisa 1
run_probe rejected_aggregate_equality examples/rejected_aggregate_equality.elisa 1
run_probe rejected_budget examples/rejected_budget.elisa 1
run_probe effect_containment examples/effect_containment.elisa 0
run_probe rejected_effect_containment examples/rejected_effect_containment.elisa 1
run_probe body_ensures examples/body_ensures.elisa 0
run_probe rejected_body_ensures examples/rejected_body_ensures.elisa 1
run_probe contract_placement examples/contract_placement.elisa 0
run_probe rejected_contract_placement examples/rejected_contract_placement.elisa 1
run_probe scalar_reference_index examples/scalar_reference_index.elisa 1
run_probe unsigned_disjunction_introduction examples/unsigned_disjunction_introduction.elisa 0
run_probe rejected_unsigned_disjunction examples/rejected_unsigned_disjunction.elisa 1
run_probe fixed_array_constant_indices examples/fixed_array_constant_indices.elisa 0
run_probe rejected_fixed_array_constant_index examples/rejected_fixed_array_constant_index.elisa 1
run_probe disjunctive_negation_fallback examples/disjunctive_negation_fallback.elisa 0
run_probe rejected_disjunctive_negation_fallback examples/rejected_disjunctive_negation_fallback.elisa 1
run_probe variable_divisor_bounds examples/variable_divisor_bounds.elisa 0
run_probe rejected_variable_divisor_bounds examples/rejected_variable_divisor_bounds.elisa 1
run_probe call_arithmetic_arguments examples/call_arithmetic_arguments.elisa 0
run_probe rejected_call_arithmetic_arguments examples/rejected_call_arithmetic_arguments.elisa 1
run_probe constant_divisor_bounds examples/constant_divisor_bounds.elisa 0
run_probe rejected_constant_divisor_bounds examples/rejected_constant_divisor_bounds.elisa 1
run_probe nested_qualified_constants examples/nested_qualified_constants.elisa 0
run_probe rejected_nested_qualified_constants examples/rejected_nested_qualified_constants.elisa 1
run_probe literal_disjunct_pruning examples/literal_disjunct_pruning.elisa 0
run_probe rejected_literal_disjunct_pruning examples/rejected_literal_disjunct_pruning.elisa 1
run_probe scaled_single_difference examples/scaled_single_difference.elisa 0
run_probe rejected_scaled_single_difference examples/rejected_scaled_single_difference.elisa 1
run_probe literal_call_arguments examples/literal_call_arguments.elisa 0
run_probe rejected_literal_call_arguments examples/rejected_literal_call_arguments.elisa 1
run_probe signed_negated_literals examples/signed_negated_literals.elisa 0
run_probe rejected_signed_negated_literals examples/rejected_signed_negated_literals.elisa 1
run_probe qualified_call_widths examples/qualified_call_widths.elisa 0
run_probe rejected_qualified_call_widths examples/rejected_qualified_call_widths.elisa 1
run_probe linear_arithmetic_tier examples/linear_arithmetic_tier.elisa 0
run_probe rejected_linear_arithmetic_tier examples/rejected_linear_arithmetic_tier.elisa 1
run_probe signed_negative_constant_replay examples/signed_negative_constant_replay.elisa 0
run_probe rejected_signed_negative_constant_replay examples/rejected_signed_negative_constant_replay.elisa 1
run_probe linear_compound_facts examples/linear_compound_facts.elisa 0
run_probe rejected_linear_compound_facts examples/rejected_linear_compound_facts.elisa 1
run_probe same_name_module_constants examples/same_name_module_constants.elisa 0
run_probe rejected_same_name_module_constants examples/rejected_same_name_module_constants.elisa 1
run_probe same_name_module_calls examples/same_name_module_calls.elisa 0
run_probe rejected_same_name_module_calls examples/rejected_same_name_module_calls.elisa 1
run_probe call_place_disjunctions examples/call_place_disjunctions.elisa 0
run_probe rejected_call_place_disjunctions examples/rejected_call_place_disjunctions.elisa 1
run_probe qualified_constant_across_call examples/qualified_constant_across_call.elisa 0
run_probe rejected_qualified_constant_across_call examples/rejected_qualified_constant_across_call.elisa 1
run_probe constant_fact_across_call examples/constant_fact_across_call.elisa 0
run_probe rejected_constant_fact_across_call examples/rejected_constant_fact_across_call.elisa 1
run_probe callee_requires_constant examples/callee_requires_constant.elisa 0
run_probe rejected_callee_requires_constant examples/rejected_callee_requires_constant.elisa 1
run_probe call_result_case_split examples/call_result_case_split.elisa 0
run_probe rejected_call_result_case_split examples/rejected_call_result_case_split.elisa 1
run_probe repeated_name_probe examples/repeated_name_probe.elisa 0
run_probe rejected_repeated_name_probe examples/rejected_repeated_name_probe.elisa 1
run_probe call_chain_disjunctive_ensure examples/call_chain_disjunctive_ensure.elisa 0
run_probe rejected_call_chain_disjunctive_ensure examples/rejected_call_chain_disjunctive_ensure.elisa 1
run_probe qualified_constant_callee_width examples/qualified_constant_callee_width.elisa 0
run_probe rejected_qualified_constant_callee_width examples/rejected_qualified_constant_callee_width.elisa 1
run_probe negative_constant_unrelated_goal examples/negative_constant_unrelated_goal.elisa 0
run_probe rejected_negative_constant_unrelated_goal examples/rejected_negative_constant_unrelated_goal.elisa 1
run_probe closed_goal_width_uniform examples/closed_goal_width_uniform.elisa 0
run_probe rejected_closed_goal_width_uniform examples/rejected_closed_goal_width_uniform.elisa 1
run_probe rejected_source_map_include examples/rejected_source_map_include.elisa 1
run_probe linear_disequality_refuted examples/linear_disequality_refuted.elisa 0
run_probe rejected_linear_disequality_refuted examples/rejected_linear_disequality_refuted.elisa 1
run_probe call_width_across_call examples/call_width_across_call.elisa 0
run_probe rejected_call_width_across_call examples/rejected_call_width_across_call.elisa 1
run_probe call_equal_to_bounded_term examples/call_equal_to_bounded_term.elisa 0
run_probe rejected_call_equal_to_bounded_term examples/rejected_call_equal_to_bounded_term.elisa 1

# A declared effect row is evidence only when every direct call resolves to a declared callee
# whose row it contains. An exceeded row is a refutation; an unresolved callee is unsupported.
python3 - "$REPORT_DIR/effect_containment.json" "$REPORT_DIR/rejected_effect_containment.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["replay"]["gaps"] == 0
assert report["summary"]["semantic_errors"] == 0
certified = {goal["name"] for goal in report["goals"] if goal["rule"] == "effect-containment"}
if not {"wider_row", "union_row", "exact_row", "no_calls", "calls_rowless"} <= certified:
    raise SystemExit("dogfood failed: a containable effect row was not certified")
rows = {d["name"]: d["effects"] for d in report["declaration_details"] if d["kind"] == "function"}
if rows.get("wider_row") != ["Memory.Allocate", "Abort.Panic"] or rows.get("pure_callee") is not None:
    raise SystemExit("dogfood failed: declared effect rows were not reported")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: adversarial effect fixture did not fail cleanly")
certified = {goal["name"] for goal in report["goals"] if goal["rule"] == "effect-containment"}
if certified & {"narrower_than_callee", "one_uncovered_callee", "opaque_callee"}:
    raise SystemExit("dogfood failed: an uncontained effect row was certified")
kinds = {finding["name"]: (finding["kind"], finding["status"]) for finding in report["findings"]}
expected = {
    "narrower_than_callee": ("effect-row-exceeded", "disproved"),
    "one_uncovered_callee": ("effect-row-exceeded", "disproved"),
    "opaque_callee": ("effect-call-opaque", "unsupported"),
}
for name, want in expected.items():
    if kinds.get(name) != want:
        raise SystemExit("dogfood failed: %s reported %s, wanted %s" % (name, kinds.get(name), want))
PY


# A budget that ran out, a goal no rule decides, and a refuted goal are three different answers.
# The report must keep them apart so an agent repairs the right thing.
python3 - "$REPORT_DIR/rejected_budget.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
if report["replay"]["gaps"] != 0 or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: budget fixture did not fail cleanly")
status = {finding["name"]: finding["status"] for finding in report["findings"]}
expected = {
    "too_wide_quantifier": "timeout",
    "too_large_model": "timeout",
    "unsupported_reasoning": "unknown",
    "false_comparison": "disproved",
    "too_many_congruence_terms": "timeout",
    "too_many_congruence_rounds": "timeout",
    "too_many_disjunctions": "timeout",
    "too_deep_conditional": "timeout",
    "too_deep_disjunctive_goal": "timeout",
}
if status != expected:
    raise SystemExit("dogfood failed: verdict states collapsed, got %s" % sorted(status.items()))
PY


# Reflexivity, symmetry, and coherence with arithmetic hold for the language's own operators, not
# for a user `__eq__`/`__cmp__`. No goal here may prove or emit a certificate.
python3 - "$REPORT_DIR/rejected_reflexivity.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: reflexivity fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: reflexivity fixture left a replay gap")
refused = {
    "reflexive_equality",
    "reflexive_order",
    "reflexive_reverse_order",
    "symmetric_equality",
    "local_reflexive_equality",
    "field_reflexive_equality",
    "field_reflexive_order",
    "element_reflexive_equality",
    "opaque_call_reflexive_equality",
    "struct_element_binder_reflexive_equality",
}
claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}
if refused & claimed:
    raise SystemExit("dogfood failed: user-defined equality was assumed reflexive for %s" % sorted(refused & claimed))
if refused - {finding["name"] for finding in report["findings"]}:
    raise SystemExit("dogfood failed: a reflexivity goal produced no diagnostic")
PY


# Ground congruence must carry an equality through every primitive scalar former and through
# no other one. The accepted fixture may not leave a replay gap, and no adversarial goal may prove
# or emit a certificate; only the arithmetic-free resource obligations are admitted there.
python3 - "$REPORT_DIR/congruence.json" "$REPORT_DIR/rejected_congruence.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["proven"] == report["summary"]["obligations"]
assert report["replay"]["gaps"] == 0
assert report["findings"] == []
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: adversarial congruence fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: adversarial congruence fixture left a replay gap")
refused = {
    "disequality_premise",
    "order_premise",
    "disjunctive_premise",
    "unrelated_operand",
    "distinct_former",
    "struct_equality_premise",
    "indexed_element",
    "constructed_aggregate",
    "call_congruence",
    "cross_width",
    "wrapping_operand",
}
claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}
if refused & claimed:
    raise SystemExit("dogfood failed: congruence admitted %s" % sorted(refused & claimed))
if refused - {finding["name"] for finding in report["findings"]}:
    raise SystemExit("dogfood failed: an adversarial congruence goal produced no diagnostic")
PY

# A comparison concluded from two terms denoting the same value needs both operands witnessed as
# primitive scalars. The producer witnesses struct fields, container counts and elements, and
# verified total-pure call results by exact term; an aggregate comparison has no witness at all.
python3 - "$REPORT_DIR/expression_witness.json" "$REPORT_DIR/rejected_aggregate_equality.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["proven"] == report["summary"]["obligations"]
assert report["replay"]["gaps"] == 0
assert report["findings"] == []
witnesses = [fact for certificate in report["certificates"] for fact in certificate["facts"] if fact["kind"] == "call" and fact["callee"]["name"] in ("__elisa_primitive_scalar_type", "__elisa_primitive_scalar_element")]
if not any(fact["arguments"][0]["kind"] == "field" for fact in witnesses):
    raise SystemExit("dogfood failed: no field witness reached a certificate")
if not any(fact["arguments"][0]["kind"] == "call" for fact in witnesses):
    raise SystemExit("dogfood failed: no verified pure call witness reached a certificate")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed":
    raise SystemExit("dogfood failed: aggregate equality fixture did not fail cleanly")
diagnostics = report["semantic_diagnostics"]
if len(diagnostics) not in (0, 2) or any(
    diagnostic["message"] != "aggregate values do not support ==; compare their contents explicitly"
    or diagnostic["detail"] != "__aggregate"
    for diagnostic in diagnostics
):
    raise SystemExit("dogfood failed: unexpected aggregate-equality diagnostics")
if report["summary"]["semantic_errors"] != len(diagnostics):
    raise SystemExit("dogfood failed: aggregate diagnostic summary is inconsistent")
if report["replay"]["gaps"] != 0 or report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: aggregate equality fixture left a replay gap")
refused = {"array_equality", "nested_array_equality", "tuple_equality", "dictionary_equality", "construct_equality", "update_equality", "quantified_array_equality", "quantified_tuple_equality", "quantified_dictionary_equality", "quantified_construct_equality"}
finding_names = {finding["name"] for finding in report["findings"]}
if refused - finding_names:
    raise SystemExit("dogfood failed: an aggregate-equality goal lacked a refusal diagnostic")
claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}
if refused & claimed:
    raise SystemExit("dogfood failed: aggregate equality admitted for %s" % sorted(refused & claimed))
print("dogfood expression_witness: term-keyed type witnesses admit exactly the primitive scalar places")
PY

# A callee reaches the caller only through references and globals, and a conjunctive guard entails
# each of its parts. Together they carry a bounded-recursion precondition past an opaque call; the
# conjuncts are derived facts, so every certificate that uses one must still replay without gaps.
python3 - "$REPORT_DIR/call_stable_facts.json" "$REPORT_DIR/rejected_call_stable_facts.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["summary"]["proven"] != report["summary"]["obligations"]:
    raise SystemExit("dogfood failed: call-stable fixture did not prove")
if report["replay"]["gaps"] != 0 or report["findings"] != []:
    raise SystemExit("dogfood failed: call-stable fixture left a gap or a finding")
origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}
if "branch-conjunct" not in origins:
    raise SystemExit("dogfood failed: no branch conjunct reached a certificate")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: call-stable boundary fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: call-stable boundary fixture left a replay gap")
refused = {"aliased_scalar", "assigned_in_branch", "disjunctive_branch", "negated_conjunctive_guard", "rebound_after_guard"}
missing = refused - {finding["name"] for finding in report["findings"]}
if missing:
    raise SystemExit("dogfood failed: no diagnostic for %s" % sorted(missing))
print("dogfood call_stable_facts: facts survive exactly the calls and joins that cannot falsify them")
PY

# Lending only shared references leaves the caller's resource state untouched, so such a call needs
# no callee body summary. Every one of them must still appear in the trace as an explicit
# shared-read transition, and a writable or escaping capability must still be refused.
python3 - "$REPORT_DIR/shared_borrow_calls.json" "$REPORT_DIR/rejected_shared_borrow_calls.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["summary"]["proven"] != report["summary"]["obligations"]:
    raise SystemExit("dogfood failed: shared-reference call fixture did not prove")
if report["replay"]["gaps"] != 0 or report["findings"] != []:
    raise SystemExit("dogfood failed: shared-reference call fixture left a gap or a finding")
shared = [node for node in report["kernel"]["nodes"] if node["kind"] == "resource-call-lend"]
if not shared:
    raise SystemExit("dogfood failed: no shared-read call reached the arena")
if any(node["left"] != 0 or node["children_count"] != node["auxiliary"] * 2 for node in shared):
    raise SystemExit("dogfood failed: a shared-read call carried a callee summary root")
nodes = report["kernel"]["nodes"]
children = report["kernel"]["children"]
formals = [nodes[child] for node in shared for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]
if not formals or any(formal["kind"] != "resource-call-formal" for formal in formals):
    raise SystemExit("dogfood failed: a shared-read call recorded no callee parameter modes")
if any(formal["operator"] not in ("value", "external-shared") for formal in formals):
    raise SystemExit("dogfood failed: an exclusive callee formal was recorded under a shared read")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: shared-reference boundary fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: shared-reference boundary fixture left a replay gap")
findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}
required = {("borrow-call-opaque", "recursive_reference_return"), ("borrow-call-opaque", "lends_shared_while_mutably_borrowed"), ("resource-use-after-move", "lends_moved_value")}
missing = required - findings
if missing:
    raise SystemExit("dogfood failed: no diagnostic for %s" % sorted(missing))
if any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"]):
    raise SystemExit("dogfood failed: an escaping, moved or exclusively borrowed capability was recorded as a lend")
opaque = {finding["name"] for finding in report["findings"] if finding["kind"] == "borrow-call-opaque"}
if "lends_shared_while_mutably_borrowed" not in opaque:
    raise SystemExit("dogfood failed: a shared lend across a live exclusive borrow was not refused")
print("dogfood shared_borrow_calls: shared lending needs no callee summary")
PY

# An exclusive lend needs no callee summary either. The callee can do no more than write through
# the reference, so the caller records a write to the whole lent place; every exclusive capability
# must be one the caller holds alone, with no overlapping live borrow and no overlapping co-lend.
python3 - "$REPORT_DIR/writable_lend_calls.json" "$REPORT_DIR/rejected_writable_lend_calls.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: confined writable lending did not prove cleanly")
nodes = report["kernel"]["nodes"]
children = report["kernel"]["children"]
lends = [node for node in nodes if node["kind"] == "resource-call-lend"]
if not lends:
    raise SystemExit("dogfood failed: no confined lend reached the arena")
formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]
if not any(formal["operator"] == "external-mutable" for formal in formals):
    raise SystemExit("dogfood failed: no exclusive lend was recorded")
if any(formal["kind"] != "resource-call-formal" for formal in formals):
    raise SystemExit("dogfood failed: a confined lend recorded no callee parameter modes")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
# The pinned frontend reports the two call-site overlaps itself; the checker must still refuse
# all three, including the live-borrow case the frontend does not see.
frontend = sorted((diagnostic["line"], diagnostic["actual"]) for diagnostic in report["semantic_diagnostics"])
if report["status"] != "failed" or frontend != [(16, "swap_pair"), (35, "read_and_write")] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: exclusive-lend boundary fixture did not fail cleanly")
if any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"]):
    raise SystemExit("dogfood failed: an unconfined exclusive capability was recorded as a lend")
opaque = {finding["name"] for finding in report["findings"] if finding["kind"] == "borrow-call-opaque"}
for name in ("swap_pair", "read_and_write", "touch_borrowed"):
    if name not in opaque:
        raise SystemExit("dogfood failed: %s was not refused" % name)
print("dogfood writable_lend_calls: an exclusive lend is confined to a whole-place write")
PY

# A lifetime parameter does not stop a call from being a lend. The callee may allocate into a
# mapped caller region and can never close one, so the claim is the lifetime pinning itself:
# every formal lifetime resolves to a region active at the call and to the actual's own region.
python3 - "$REPORT_DIR/region_lend_calls.json" "$REPORT_DIR/rejected_region_lend_calls.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: region-polymorphic lending did not prove cleanly")
nodes = report["kernel"]["nodes"]
children = report["kernel"]["children"]
lends = [node for node in nodes if node["kind"] == "resource-call-lend" and node["right"] > 0]
if not lends:
    raise SystemExit("dogfood failed: no lifetime-carrying lend reached the arena")
for node in lends:
    if node["children_count"] != node["auxiliary"] * 2 + node["right"]:
        raise SystemExit("dogfood failed: a lend child list does not match its parameter and lifetime counts")
    entries = [nodes[child] for child in children[node["children_start"] + node["auxiliary"] * 2:node["children_start"] + node["children_count"]]]
    if any(entry["kind"] != "resource-call-region" or entry["operator"] != "param" or not entry["name"] or not entry["secondary_name"] for entry in entries):
        raise SystemExit("dogfood failed: a lifetime map entry is malformed")
    if len({entry["name"] for entry in entries}) != len(entries):
        raise SystemExit("dogfood failed: a formal lifetime was pinned twice")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0 or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: lifetime boundary fixture did not fail cleanly")
if any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"]):
    raise SystemExit("dogfood failed: an unpinned lifetime was recorded as a lend")
print("dogfood region_lend_calls: a lifetime parameter is pinned, never assumed")
PY

# A region-polymorphic callee that does have a summary must compose into its caller. This replayed
