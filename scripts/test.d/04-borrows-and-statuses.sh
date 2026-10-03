# shellcheck shell=bash
# Part 4 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/value_match_named_payload.elisa" >/dev/null
value_match_named_payload_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/catch_pure_arm_call.elisa" >/dev/null
catch_pure_arm_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/catch_nested_pure_arm_call.elisa" >/dev/null
catch_nested_pure_arm_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/value_match_nested_pure_call.elisa" >/dev/null
value_match_nested_pure_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/index_call_summary.elisa" >/dev/null
index_call_summary_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/indexn_call_summary.elisa" >/dev/null
indexn_call_summary_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/slice_call_summary.elisa" >/dev/null
slice_call_summary_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/resource_branch_join.elisa" >/dev/null
resource_branch_join_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_write.elisa" >/dev/null
rejected_borrow_write_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_alias.elisa" >/dev/null
rejected_borrow_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_field_write.elisa" >/dev/null
rejected_borrow_field_write_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_field_alias.elisa" >/dev/null
rejected_borrow_field_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_nested_prefix.elisa" >/dev/null
rejected_borrow_nested_prefix_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_move_parent.elisa" >/dev/null
rejected_borrow_move_parent_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_resource_use_after_move.elisa" >/dev/null
rejected_resource_use_after_move_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_move.elisa" >/dev/null
rejected_borrow_move_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_escape.elisa" >/dev/null
rejected_borrow_escape_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_call.elisa" >/dev/null
rejected_borrow_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_index_alias.elisa" >/dev/null
rejected_borrow_index_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_multi_index_alias.elisa" >/dev/null
rejected_borrow_multi_index_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_dynamic_alias.elisa" >/dev/null
rejected_borrow_dynamic_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_dynamic_multi_alias.elisa" >/dev/null
rejected_borrow_dynamic_multi_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_call_alias.elisa" >/dev/null
rejected_borrow_call_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_resource_branch_move.elisa" >/dev/null
rejected_resource_branch_move_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_mutable_source.elisa" >/dev/null
rejected_borrow_mutable_source_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_nested_catch.elisa" >/dev/null
rejected_borrow_nested_catch_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_nested_match.elisa" >/dev/null
rejected_borrow_nested_match_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_value_match_impure_call.elisa" >/dev/null
rejected_value_match_impure_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/with_include.elisa" >/dev/null
include_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/include_macro.elisa" >/dev/null
if [[ "$?" -ne 0 ]]; then
    include_status=1
fi
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/lemma.elisa" >/dev/null
lemma_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/recursive_lemma_decreases.elisa" >/dev/null
recursive_lemma_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/mutual_recursive_lemmas.elisa" >/dev/null
mutual_recursive_lemmas_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/lexicographic_recursive_lemma.elisa" >/dev/null
lexicographic_recursive_lemma_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/function_summary.elisa" >/dev/null
summary_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/framed_call.elisa" >/dev/null
framed_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/nested_frame.elisa" >/dev/null
nested_frame_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/indexed_frame.elisa" >/dev/null
indexed_frame_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/header_frame.elisa" >/dev/null
header_frame_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/branch_negation.elisa" >/dev/null
branch_negation_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/old_state.elisa" >/dev/null
old_state_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/structured_result.elisa" >/dev/null
structured_result_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/assert_by_local.elisa" >/dev/null
assert_by_local_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/pattern_proof.elisa" >/dev/null
pattern_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/total_match.elisa" >/dev/null
total_match_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/arithmetic_identity.elisa" >/dev/null
arithmetic_identity_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/equality_alias.elisa" >/dev/null
equality_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/quantifier.elisa" >/dev/null
quantifier_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/collection_quantifier.elisa" >/dev/null
collection_quantifier_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/void_postcondition.elisa" >/dev/null
void_postcondition_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/multiple_invariants.elisa" >/dev/null
multiple_invariants_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/named_arguments.elisa" >/dev/null
named_arguments_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/default_arguments.elisa" >/dev/null
default_arguments_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/assignment_rhs_state.elisa" >/dev/null
assignment_rhs_state_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/pure_contract_call.elisa" >/dev/null
pure_contract_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/recursive_pure_contract_call.elisa" >/dev/null
recursive_pure_contract_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/pure_default_contract_call.elisa" >/dev/null
pure_default_contract_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/mutual_recursive_pure_contract_call.elisa" >/dev/null
mutual_recursive_pure_contract_call_status=$?
run_json_report "$ROOT_DIR/examples/structural_recursive_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0'
structural_recursive_summary_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_structural_recursive_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] != "proved"; assert sorted((finding["kind"], finding["name"]) for finding in report["findings"]) == [("ensure-unproven", "rejected_shadowed_payload"), ("ensure-unproven", "rejected_structural_depth")]'
rejected_structural_recursive_summary_status=${PIPESTATUS[1]}
if [[ "$structural_recursive_summary_status" -ne 0 || "$rejected_structural_recursive_summary_status" -ne 0 ]]; then
    printf 'structural recursive summary checks failed: proved=%s rejected=%s\n' "$structural_recursive_summary_status" "$rejected_structural_recursive_summary_status" >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/recursive_decreases.elisa" >/dev/null
recursive_decreases_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/mutual_decreases.elisa" >/dev/null
mutual_decreases_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/mutual_structural_decreases.elisa" >/dev/null
mutual_structural_decreases_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/lexicographic_decreases.elisa" >/dev/null
lexicographic_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/structural_decreases.elisa" >/dev/null
structural_decreases_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/difference_constraints.elisa" >/dev/null
difference_constraints_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/disjunctive_facts.elisa" >/dev/null
disjunctive_facts_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/modulo_division_bounds.elisa" >/dev/null
modulo_division_bounds_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected.elisa" >/dev/null
rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_lemma.elisa" >/dev/null
rejected_lemma_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_self_assert.elisa" >/dev/null
self_assert_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_overflow.elisa" >/dev/null
overflow_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_underflow.elisa" >/dev/null
underflow_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_min_modulo_overflow.elisa" >/dev/null
rejected_min_modulo_overflow_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_stale_branch.elisa" >/dev/null
stale_branch_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_branch_stale_return.elisa" >/dev/null
branch_stale_return_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_fallthrough.elisa" >/dev/null
fallthrough_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_invariant.elisa" >/dev/null
invariant_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_for_invariant.elisa" >/dev/null
rejected_for_invariant_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_for_invariant_scope.elisa" >/dev/null
rejected_for_invariant_scope_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_call_precondition.elisa" >/dev/null
call_precondition_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_lemma_result.elisa" >/dev/null
lemma_result_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_compound_assignment.elisa" >/dev/null
compound_assignment_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_frame_write.elisa" >/dev/null
frame_write_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_counterexample.elisa" >/dev/null
counterexample_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_frame_preserve.elisa" >/dev/null
frame_preserve_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_frame_call.elisa" >/dev/null
frame_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_nested_frame.elisa" >/dev/null
rejected_nested_frame_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_deep_frame.elisa" >/dev/null
rejected_deep_frame_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_indexed_frame.elisa" >/dev/null
rejected_indexed_frame_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_index_bounds.elisa" >/dev/null
rejected_index_bounds_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_index_call.elisa" >/dev/null
rejected_index_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_index_pure_result.elisa" >/dev/null
rejected_index_pure_result_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_fixed_array_bounds.elisa" >/dev/null
rejected_fixed_array_bounds_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_slice_bounds.elisa" >/dev/null
rejected_slice_bounds_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_fixed_array_slice_bounds.elisa" >/dev/null
rejected_fixed_array_slice_bounds_status=$?
run_json_report "$ROOT_DIR/examples/captured_structural_accumulator.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert all(goal["proven"] for goal in report["goals"] if goal["rule"] == "structural-safety"); assert report["replay"]["gaps"] == 0'
captured_structural_accumulator_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_field_alias.elisa" >/dev/null
rejected_field_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_header_frame.elisa" >/dev/null
header_frame_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_header_frame_root.elisa" >/dev/null
header_frame_root_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_frame_condition_call.elisa" >/dev/null
frame_condition_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_frame_alias.elisa" >/dev/null
frame_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_old_call.elisa" >/dev/null
old_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_quantifier.elisa" >/dev/null
quantifier_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_collection_quantifier.elisa" >/dev/null
collection_quantifier_rejected_status=$?
run_json_report "$ROOT_DIR/examples/rejected_quantifier_capture.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert not any(goal["rule"] == "quantifier-forall" and goal["proven"] for goal in report["goals"]); assert any(finding["kind"] == "ensure-unproven" and finding["name"] == "dictionary_key_name_must_not_be_captured" for finding in report["findings"])'
quantifier_capture_statuses=("${PIPESTATUS[@]}")
if [[ "${quantifier_capture_statuses[0]}" -ne 1 || "${quantifier_capture_statuses[1]}" -ne 0 ]]; then
    printf 'proof test matrix failed: dictionary quantifier binder capture was not rejected cleanly\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_void_postcondition.elisa" >/dev/null
void_postcondition_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_named_arguments.elisa" >/dev/null
named_arguments_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_default_arguments.elisa" >/dev/null
default_arguments_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_assert_call_stale.elisa" >/dev/null
assert_call_stale_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_assert_by_call_stale.elisa" >/dev/null
assert_by_call_stale_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_decreases.elisa" >/dev/null
decreases_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_loop_break.elisa" >/dev/null
loop_break_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_loop_control_invariant.elisa" >/dev/null
rejected_loop_control_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_getelse_recovery.elisa" >/dev/null
rejected_getelse_recovery_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_catch_error_postcondition.elisa" >/dev/null
rejected_catch_error_postcondition_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_continue_decreases_nonprogress.elisa" >/dev/null
rejected_continue_decreases_nonprogress_status=$?
run_json_report "$ROOT_DIR/examples/rejected_continue_decreases_nonprogress.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "loop-decreases-unproven" for finding in report["findings"])'
rejected_continue_decreases_nonprogress_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_continue_decreases_nonprogress_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: non-progressing continue edge was not rejected by termination checking\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_recursive_summary.elisa" >/dev/null
recursive_summary_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_recursive_decreases.elisa" >/dev/null
recursive_decreases_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_recursive_assert.elisa" >/dev/null
recursive_assert_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_recursive_lemma.elisa" >/dev/null
recursive_lemma_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_recursive_lemma_decreases.elisa" >/dev/null
recursive_lemma_decreases_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_recursive_lemma_in_proof_block.elisa" >/dev/null
recursive_lemma_in_proof_block_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_lexicographic_decreases.elisa" >/dev/null
lexicographic_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_nested_call_precondition.elisa" >/dev/null
nested_call_precondition_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_structural_decreases.elisa" >/dev/null
structural_decreases_rejected_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_structural_decreases_star.elisa" >/dev/null
structural_decreases_star_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_structural_shadow.elisa" >/dev/null
structural_shadow_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_mutual_structural_decreases.elisa" >/dev/null
rejected_mutual_structural_decreases_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_decreases_post_nonnegative.elisa" >/dev/null
decreases_post_nonnegative_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_difference_constraints.elisa" >/dev/null
rejected_difference_constraints_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_disjunctive_facts.elisa" >/dev/null
rejected_disjunctive_facts_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_modulo_division_bounds.elisa" >/dev/null
rejected_modulo_division_bounds_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_impure_proof.elisa" >/dev/null
rejected_impure_proof_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_nested_call_symbolic_value.elisa" >/dev/null
rejected_nested_call_symbolic_value_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_loop_invariant_scope.elisa" >/dev/null
rejected_loop_invariant_scope_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_checked_index_nested.elisa" >/dev/null
rejected_checked_index_nested_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_for_shadow.elisa" >/dev/null
rejected_for_shadow_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_match_shadow.elisa" >/dev/null
rejected_match_shadow_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_match_shadow_fact.elisa" >/dev/null
rejected_match_shadow_fact_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_value_match.elisa" >/dev/null
rejected_value_match_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_value_match_payload_shadow.elisa" >/dev/null
rejected_value_match_payload_shadow_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_value_match_positional_payload.elisa" >/dev/null
rejected_value_match_positional_payload_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_catch_impure_arm_call.elisa" >/dev/null
rejected_catch_impure_arm_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_contract_call.elisa" >/dev/null
rejected_contract_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_mutable_pure_contract.elisa" >/dev/null
rejected_mutable_pure_contract_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_pure_default_contract.elisa" >/dev/null
rejected_pure_default_contract_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_resource_expression.elisa" >/dev/null
rejected_resource_expression_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_parallel_proof_state.elisa" >/dev/null
rejected_parallel_proof_state_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_parallel_nested_state.elisa" >/dev/null
rejected_parallel_nested_state_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_move_use_after.elisa" >/dev/null
rejected_move_use_after_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_early_return_index_guard.elisa" >/dev/null
rejected_early_return_index_guard_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_unknown_call_result.elisa" >/dev/null
rejected_unknown_call_result_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_unknown_assert_reuse.elisa" >/dev/null
rejected_unknown_assert_reuse_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_assert_nested_call.elisa" >/dev/null
rejected_assert_nested_call_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_mutual_recursive_pure_impure_member.elisa" >/dev/null
rejected_mutual_recursive_pure_impure_member_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_mutable_global_pure_contract.elisa" >/dev/null
rejected_mutable_global_pure_contract_status=$?
run_json_report "$ROOT_DIR/examples/borrow_shared_read.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(certificate["rule"] == "resource-safety" and certificate["replayed"] for certificate in report["certificates"]); assert any(node["kind"] == "resource-safety" for node in report["kernel"]["nodes"])'
borrow_shared_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_mutable_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(certificate["rule"] == "resource-safety" and certificate["replayed"] for certificate in report["certificates"]); assert any(node["kind"] == "resource-safety" for node in report["kernel"]["nodes"])'
borrow_mutable_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_lexical_scope.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(certificate["rule"] == "resource-safety" and certificate["replayed"] for certificate in report["certificates"]); assert any(node["kind"] == "resource-safety" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-scope" for node in report["kernel"]["nodes"])'
borrow_lexical_scope_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_disjoint_fields.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "field" and node["name"] == "left" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "field" and node["name"] == "right" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-write" and node["left"] != 0 for node in report["kernel"]["nodes"])'
borrow_disjoint_fields_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_nested_disjoint_fields.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert sum(1 for node in report["kernel"]["nodes"] if node["kind"] == "field" and node["name"] == "value") >= 1; assert sum(1 for node in report["kernel"]["nodes"] if node["kind"] == "field" and node["name"] == "sibling") >= 1'
borrow_nested_disjoint_fields_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_four_nested_fields.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "field" and node["name"] == "value" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "field" and node["name"] == "sibling" for node in report["kernel"]["nodes"])'
borrow_four_nested_fields_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_move_disjoint_field.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-move" and node["left"] != 0 for node in report["kernel"]["nodes"])'
borrow_move_disjoint_field_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "read_ref" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call-arg" and node["operator"] == "reference" for node in report["kernel"]["nodes"])'
borrow_call_summary_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_indexed_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "index" and node["value"] in (0, 1) for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call" and node["name"] == "read_index_ref" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call-arg" and node["operator"] == "borrow" for node in report["kernel"]["nodes"])'
borrow_indexed_places_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_multi_indexed_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert sum(node["kind"] == "index" for node in report["kernel"]["nodes"]) >= 4'
borrow_multi_indexed_places_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_dynamic_whole_root.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-bind" and node["operator"] == "shared" for node in report["kernel"]["nodes"])'
borrow_dynamic_whole_root_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_dynamic_multi_whole_root.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-bind" and node["operator"] == "shared" for node in report["kernel"]["nodes"])'
borrow_dynamic_multi_whole_root_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_symbolic_disjoint.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-disjoint" and node["operator"] == "!=" for node in report["kernel"]["nodes"])'
borrow_symbolic_disjoint_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_nested_expression.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "borrow_nested_catch_reader" for node in report["kernel"]["nodes"])'
borrow_nested_expression_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/borrow_reference_return_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "return_reference" for node in report["kernel"]["nodes"])'
borrow_reference_return_summary_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/value_match_pure_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "value_match_pure_call_leaf" for goal in report["goals"] for dependency in goal["dependencies"])'
value_match_pure_call_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/value_match_named_payload.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "value_match_named_payload_leaf" for goal in report["goals"] for dependency in goal["dependencies"])'
value_match_named_payload_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/catch_pure_arm_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "catch_pure_arm_value" for goal in report["goals"] for dependency in goal["dependencies"])'
catch_pure_arm_call_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_value_match_payload_shadow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "ensure-unproven" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_value_match_payload_shadow_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_value_match_positional_payload.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_value_match_positional_payload_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_catch_impure_arm_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_catch_impure_arm_call_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/nested_frame.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "set_inner_value" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call" and node["name"] == "set_inner_ref" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call-arg" and node["operator"] == "borrow" and node["name"] == "inner" for node in report["kernel"]["nodes"])'
nested_frame_resource_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/resource_branch_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-join-move" and node["name"] == "x" for node in report["kernel"]["nodes"])'
resource_branch_join_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_write_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_field_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_field_write_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_field_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_field_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_nested_prefix.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_nested_prefix_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_four_nested_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_four_nested_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_move_parent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-move-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_move_parent_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_resource_use_after_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "resource-use-after-move" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_resource_use_after_move_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-move-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_move_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_escape.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-escape" and finding["status"] == "unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_escape_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert not any(finding["kind"] == "borrow-call-opaque" for finding in report["findings"]); findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("index-upper-unproven", "opaque_dynamic_borrow") in findings; assert ("index-upper-unproven", "opaque_dynamic_write") in findings; assert ("function-summary-unverified", "rejected_borrow_call") in findings; assert ("function-summary-unverified", "rejected_writable_borrow_call") in findings; assert report["replay"]["gaps"] == 0'
rejected_borrow_call_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_index_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_index_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_multi_index_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_multi_index_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_dynamic_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-overlap-unproven" and finding["status"] == "unknown" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_dynamic_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_dynamic_multi_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-overlap-unproven" and finding["status"] == "unknown" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_dynamic_multi_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_symbolic_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-overlap-unproven" and finding["status"] == "unknown" for finding in report["findings"]); assert report["replay"]["gaps"] == 0; assert not any(node["kind"] == "resource-disjoint" for node in report["kernel"]["nodes"])'
rejected_borrow_symbolic_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_call_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-call-summary-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert not any(node["kind"] == "resource-call" and node["name"] == "set_inner_ref" for node in report["kernel"]["nodes"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_call_alias_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_resource_branch_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "resource-use-after-move" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_resource_branch_move_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_mutable_source.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-mutable-source" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_mutable_source_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_nested_catch.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-escape" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(node["kind"] == "resource-call" and node["name"] == "borrow_catch_source" for node in report["kernel"]["nodes"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_nested_catch_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_borrow_nested_match.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-escape" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(node["kind"] == "resource-call" and node["name"] == "borrow_match_reader" for node in report["kernel"]["nodes"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_nested_match_probe_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_value_match_impure_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "expression-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_value_match_impure_call_probe_status=${PIPESTATUS[1]}
set -e

if [[ "$total_match_status" -ne 0 ]]; then
    printf 'proof test matrix failed: total_match=%s\n' "$total_match_status" >&2
    exit 1
fi

if [[ "$bounded_model_status" -ne 0 || "$dogfood_kernel_status" -ne 0 || "$dogfood_kernel_core_status" -ne 0 || "$rejected_dogfood_kernel_core_status" -ne 1 ]]; then
    printf 'proof test matrix failed: bounded_model=%s dogfood_kernel=%s dogfood_kernel_core=%s rejected_dogfood_kernel_core=%s\n' "$bounded_model_status" "$dogfood_kernel_status" "$dogfood_kernel_core_status" "$rejected_dogfood_kernel_core_status" >&2
    exit 1
fi

if [[ "$verified_status" -ne 0 || "$include_status" -ne 0 || "$lemma_status" -ne 0 || "$recursive_lemma_status" -ne 0 || "$mutual_recursive_lemmas_status" -ne 0 || "$lexicographic_recursive_lemma_status" -ne 0 || "$summary_status" -ne 0 || "$framed_call_status" -ne 0 || "$header_frame_status" -ne 0 || "$branch_negation_status" -ne 0 || "$old_state_status" -ne 0 || "$structured_result_status" -ne 0 || "$assert_by_local_status" -ne 0 || "$pattern_status" -ne 0 || "$arithmetic_identity_status" -ne 0 || "$equality_alias_status" -ne 0 || "$quantifier_status" -ne 0 || "$void_postcondition_status" -ne 0 || "$named_arguments_status" -ne 0 || "$default_arguments_status" -ne 0 || "$assignment_rhs_state_status" -ne 0 || "$pure_contract_call_status" -ne 0 || "$recursive_pure_contract_call_status" -ne 0 || "$pure_default_contract_call_status" -ne 0 || "$mutual_recursive_pure_contract_call_status" -ne 0 || "$recursive_decreases_status" -ne 0 || "$mutual_decreases_status" -ne 0 || "$move_runtime_status" -ne 0 || "$rejected_status" -ne 1 || "$rejected_lemma_status" -ne 1 || "$self_assert_status" -ne 1 || "$overflow_status" -ne 1 || "$underflow_status" -ne 1 || "$rejected_min_modulo_overflow_status" -ne 1 || "$stale_branch_status" -ne 1 || "$fallthrough_status" -ne 1 || "$invariant_status" -ne 1 || "$rejected_for_invariant_status" -ne 1 || "$rejected_for_invariant_scope_status" -ne 1 || "$call_precondition_status" -ne 1 || "$lemma_result_status" -ne 1 || "$compound_assignment_status" -ne 1 || "$frame_write_status" -ne 1 || "$frame_preserve_status" -ne 1 || "$frame_call_status" -ne 1 || "$header_frame_rejected_status" -ne 1 || "$header_frame_root_rejected_status" -ne 1 || "$frame_condition_status" -ne 1 || "$frame_alias_status" -ne 1 || "$old_call_status" -ne 1 || "$quantifier_rejected_status" -ne 1 || "$void_postcondition_rejected_status" -ne 1 || "$named_arguments_rejected_status" -ne 1 || "$default_arguments_rejected_status" -ne 1 || "$assert_call_stale_status" -ne 1 || "$assert_by_call_stale_status" -ne 1 || "$decreases_rejected_status" -ne 1 || "$recursive_summary_rejected_status" -ne 1 || "$recursive_decreases_rejected_status" -ne 1 || "$recursive_assert_rejected_status" -ne 1 || "$recursive_lemma_rejected_status" -ne 1 || "$recursive_lemma_decreases_rejected_status" -ne 1 ]]; then
    printf 'proof test matrix failed: verified=%s include=%s lemma=%s summary=%s framed_call=%s header_frame=%s branch_negation=%s old_state=%s structured_result=%s assert_by_local=%s arithmetic_identity=%s equality_alias=%s quantifier=%s void_postcondition=%s named_arguments=%s default_arguments=%s assignment_rhs_state=%s recursive_decreases=%s mutual_decreases=%s rejected=%s rejected_lemma=%s self_assert=%s overflow=%s stale_branch=%s fallthrough=%s invariant=%s call_precondition=%s lemma_result=%s compound_assignment=%s frame_write=%s frame_preserve=%s frame_call=%s header_frame_rejected=%s header_frame_root_rejected=%s frame_condition=%s frame_alias=%s old_call=%s quantifier_rejected=%s void_postcondition_rejected=%s named_arguments_rejected=%s default_arguments_rejected=%s assert_call_stale=%s assert_by_call_stale=%s decreases_rejected=%s loop_break_rejected=%s recursive_summary_rejected=%s recursive_decreases_rejected=%s recursive_assert_rejected=%s\n' "$verified_status" "$include_status" "$lemma_status" "$summary_status" "$framed_call_status" "$header_frame_status" "$branch_negation_status" "$old_state_status" "$structured_result_status" "$assert_by_local_status" "$arithmetic_identity_status" "$equality_alias_status" "$quantifier_status" "$void_postcondition_status" "$named_arguments_status" "$default_arguments_status" "$assignment_rhs_state_status" "$recursive_decreases_status" "$mutual_decreases_status" "$rejected_status" "$rejected_lemma_status" "$self_assert_status" "$overflow_status" "$stale_branch_status" "$fallthrough_status" "$invariant_status" "$call_precondition_status" "$lemma_result_status" "$compound_assignment_status" "$frame_write_status" "$frame_preserve_status" "$frame_call_status" "$header_frame_rejected_status" "$header_frame_root_rejected_status" "$frame_condition_status" "$frame_alias_status" "$old_call_status" "$quantifier_rejected_status" "$void_postcondition_rejected_status" "$named_arguments_rejected_status" "$default_arguments_rejected_status" "$assert_call_stale_status" "$assert_by_call_stale_status" "$decreases_rejected_status" "$loop_break_rejected_status" "$recursive_summary_rejected_status" "$recursive_decreases_rejected_status" "$recursive_assert_rejected_status" >&2
    exit 1
fi

if [[ "$collection_quantifier_status" -ne 0 || "$collection_quantifier_rejected_status" -ne 1 || "$multiple_invariants_status" -ne 0 || "$branch_stale_return_status" -ne 1 || "$recursive_lemma_rejected_status" -ne 1 || "$recursive_lemma_decreases_rejected_status" -ne 1 || "$recursive_lemma_in_proof_block_rejected_status" -ne 1 || "$loop_break_rejected_status" -ne 1 || "$rejected_loop_control_status" -ne 1 || "$rejected_getelse_recovery_status" -ne 1 || "$rejected_catch_error_postcondition_status" -ne 1 || "$rejected_continue_decreases_nonprogress_status" -ne 1 || "$lexicographic_status" -ne 0 || "$lexicographic_rejected_status" -ne 1 || "$nested_call_precondition_status" -ne 1 || "$structural_decreases_status" -ne 0 || "$mutual_structural_decreases_status" -ne 0 || "$difference_constraints_status" -ne 0 || "$disjunctive_facts_status" -ne 0 || "$structural_decreases_rejected_status" -ne 1 || "$structural_decreases_star_status" -ne 1 || "$structural_shadow_status" -ne 1 || "$rejected_mutual_structural_decreases_status" -ne 1 || "$decreases_post_nonnegative_status" -ne 1 || "$rejected_difference_constraints_status" -ne 1 || "$rejected_disjunctive_facts_status" -ne 1 || "$rejected_impure_proof_status" -ne 1 ]]; then
    printf 'proof test matrix failed: collection_quantifier=%s collection_quantifier_rejected=%s multiple_invariants=%s branch_stale_return=%s recursive_lemma=%s recursive_lemma_decreases_rejected=%s recursive_lemma_in_proof_block_rejected=%s loop_break_rejected=%s rejected_loop_control=%s rejected_getelse_recovery=%s rejected_catch_error_postcondition=%s rejected_continue_decreases_nonprogress=%s lexicographic=%s lexicographic_rejected=%s nested_call_precondition=%s structural_decreases=%s mutual_structural_decreases=%s difference_constraints=%s disjunctive_facts=%s structural_decreases_rejected=%s structural_decreases_star=%s structural_shadow=%s decreases_post_nonnegative=%s rejected_difference_constraints=%s rejected_disjunctive_facts=%s rejected_impure_proof=%s\n' "$collection_quantifier_status" "$collection_quantifier_rejected_status" "$multiple_invariants_status" "$branch_stale_return_status" "$recursive_lemma_rejected_status" "$recursive_lemma_decreases_rejected_status" "$recursive_lemma_in_proof_block_rejected_status" "$loop_break_rejected_status" "$rejected_loop_control_status" "$rejected_getelse_recovery_status" "$rejected_catch_error_postcondition_status" "$rejected_continue_decreases_nonprogress_status" "$lexicographic_status" "$lexicographic_rejected_status" "$nested_call_precondition_status" "$structural_decreases_status" "$mutual_structural_decreases_status" "$difference_constraints_status" "$disjunctive_facts_status" "$structural_decreases_rejected_status" "$structural_decreases_star_status" "$structural_shadow_status" "$decreases_post_nonnegative_status" "$rejected_difference_constraints_status" "$rejected_disjunctive_facts_status" "$rejected_impure_proof_status" >&2
    exit 1
fi

if [[ "$rejected_nested_call_symbolic_value_status" -ne 1 || "$rejected_for_shadow_status" -ne 1 || "$rejected_match_shadow_status" -ne 1 || "$rejected_match_shadow_fact_status" -ne 1 || "$rejected_value_match_status" -ne 1 || "$rejected_loop_invariant_scope_status" -ne 1 || "$rejected_contract_call_status" -ne 1 || "$rejected_mutable_pure_contract_status" -ne 1 || "$rejected_pure_default_contract_status" -ne 1 || "$rejected_resource_expression_status" -ne 1 || "$rejected_unknown_call_result_status" -ne 1 || "$rejected_unknown_assert_reuse_status" -ne 1 || "$rejected_assert_nested_call_status" -ne 1 || "$rejected_mutual_recursive_pure_impure_member_status" -ne 1 || "$rejected_mutable_global_pure_contract_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_nested_call_symbolic_value=%s rejected_for_shadow=%s rejected_match_shadow=%s rejected_match_shadow_fact=%s rejected_value_match=%s rejected_loop_invariant_scope=%s rejected_contract_call=%s rejected_mutable_pure_contract=%s rejected_pure_default_contract=%s rejected_resource_expression=%s rejected_parallel_proof_state=%s rejected_unknown_call_result=%s rejected_unknown_assert_reuse=%s rejected_assert_nested_call=%s rejected_mutual_recursive_pure_impure_member=%s rejected_mutable_global_pure_contract=%s\n' "$rejected_nested_call_symbolic_value_status" "$rejected_for_shadow_status" "$rejected_match_shadow_status" "$rejected_match_shadow_fact_status" "$rejected_value_match_status" "$rejected_loop_invariant_scope_status" "$rejected_contract_call_status" "$rejected_mutable_pure_contract_status" "$rejected_pure_default_contract_status" "$rejected_resource_expression_status" "$rejected_parallel_proof_state_status" "$rejected_unknown_call_result_status" "$rejected_unknown_assert_reuse_status" "$rejected_assert_nested_call_status" "$rejected_mutual_recursive_pure_impure_member_status" "$rejected_mutable_global_pure_contract_status" >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_parallel_proof_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "parallel-state-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(goal["rule"] == "goal" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
parallel_boundary_probe_status=${PIPESTATUS[1]}
set -e
if [[ "$parallel_boundary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: parallel loop leaked sequential proof state\n' >&2
    exit 1
fi

if [[ "$rejected_parallel_nested_state_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_parallel_nested_state=%s\n' "$rejected_parallel_nested_state_status" >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_parallel_nested_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "parallel-state-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(goal["rule"] == "goal" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
parallel_nested_boundary_probe_status=${PIPESTATUS[1]}
set -e
if [[ "$parallel_nested_boundary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested parallel loop leaked sequential proof state\n' >&2
    exit 1
fi

if [[ "$rejected_move_use_after_status" -ne 1 || "$rejected_early_return_index_guard_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_move_use_after=%s rejected_early_return_index_guard=%s\n' "$rejected_move_use_after_status" "$rejected_early_return_index_guard_status" >&2
    exit 1
fi

if [[ "$borrow_nested_expression_status" -ne 0 || "$borrow_nested_expression_probe_status" -ne 0 || "$borrow_reference_return_summary_status" -ne 0 || "$borrow_reference_return_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested borrow result status=%s probe=%s reference return status=%s probe=%s\n' "$borrow_nested_expression_status" "$borrow_nested_expression_probe_status" "$borrow_reference_return_summary_status" "$borrow_reference_return_summary_probe_status" >&2
    exit 1
fi

if [[ "$value_match_pure_call_status" -ne 0 || "$value_match_pure_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pure value-match call status=%s probe=%s\n' "$value_match_pure_call_status" "$value_match_pure_call_probe_status" >&2
    exit 1
fi

if [[ "$value_match_named_payload_status" -ne 0 || "$value_match_named_payload_probe_status" -ne 0 || "$catch_pure_arm_call_status" -ne 0 || "$catch_pure_arm_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: named payload value-match=%s/%s catch pure arm=%s/%s\n' "$value_match_named_payload_status" "$value_match_named_payload_probe_status" "$catch_pure_arm_call_status" "$catch_pure_arm_call_probe_status" >&2
    exit 1
fi

if [[ "$index_call_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pure index result summary status=%s\n' "$index_call_summary_status" >&2
    exit 1
fi

if [[ "$indexn_call_summary_status" -ne 0 || "$slice_call_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: indexn summary=%s slice summary=%s\n' "$indexn_call_summary_status" "$slice_call_summary_status" >&2
    exit 1
fi

if [[ "$catch_nested_pure_arm_call_status" -ne 0 || "$value_match_nested_pure_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested pure catch arm=%s value-match arm=%s\n' "$catch_nested_pure_arm_call_status" "$value_match_nested_pure_call_status" >&2
    exit 1
fi

if [[ "$rejected_value_match_impure_call_status" -ne 1 || "$rejected_value_match_impure_call_probe_status" -ne 0 || "$rejected_value_match_payload_shadow_status" -ne 1 || "$rejected_value_match_payload_shadow_probe_status" -ne 0 || "$rejected_value_match_positional_payload_status" -ne 1 || "$rejected_value_match_positional_payload_probe_status" -ne 0 || "$rejected_catch_impure_arm_call_status" -ne 1 || "$rejected_catch_impure_arm_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: value-match negatives impure=%s/%s payload_shadow=%s/%s positional_payload=%s/%s catch_impure_arm=%s/%s\n' "$rejected_value_match_impure_call_status" "$rejected_value_match_impure_call_probe_status" "$rejected_value_match_payload_shadow_status" "$rejected_value_match_payload_shadow_probe_status" "$rejected_value_match_positional_payload_status" "$rejected_value_match_positional_payload_probe_status" "$rejected_catch_impure_arm_call_status" "$rejected_catch_impure_arm_call_probe_status" >&2
    exit 1
fi

if [[ "$borrow_dynamic_whole_root_status" -ne 0 || "$rejected_borrow_dynamic_alias_status" -ne 1 || "$borrow_dynamic_whole_root_probe_status" -ne 0 || "$rejected_borrow_dynamic_alias_probe_status" -ne 0 || "$borrow_dynamic_multi_whole_root_status" -ne 0 || "$rejected_borrow_dynamic_multi_alias_status" -ne 1 || "$borrow_dynamic_multi_whole_root_probe_status" -ne 0 || "$rejected_borrow_dynamic_multi_alias_probe_status" -ne 0 || "$borrow_symbolic_disjoint_status" -ne 0 || "$rejected_borrow_symbolic_alias_status" -ne 1 || "$borrow_symbolic_disjoint_probe_status" -ne 0 || "$rejected_borrow_symbolic_alias_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: dynamic resource borrow widening single=%s/%s/%s/%s multi=%s/%s/%s/%s symbolic=%s/%s/%s/%s\n' "$borrow_dynamic_whole_root_status" "$borrow_dynamic_whole_root_probe_status" "$rejected_borrow_dynamic_alias_status" "$rejected_borrow_dynamic_alias_probe_status" "$borrow_dynamic_multi_whole_root_status" "$borrow_dynamic_multi_whole_root_probe_status" "$rejected_borrow_dynamic_multi_alias_status" "$rejected_borrow_dynamic_multi_alias_probe_status" "$borrow_symbolic_disjoint_status" "$borrow_symbolic_disjoint_probe_status" "$rejected_borrow_symbolic_alias_status" "$rejected_borrow_symbolic_alias_probe_status" >&2
    exit 1
fi

if [[ "$borrow_shared_status" -ne 0 || "$borrow_mutable_status" -ne 0 || "$borrow_lexical_scope_status" -ne 0 || "$borrow_disjoint_fields_status" -ne 0 || "$borrow_nested_disjoint_fields_status" -ne 0 || "$borrow_four_nested_fields_status" -ne 0 || "$borrow_move_disjoint_field_status" -ne 0 || "$borrow_call_summary_status" -ne 0 || "$borrow_indexed_places_status" -ne 0 || "$borrow_multi_indexed_places_status" -ne 0 || "$resource_branch_join_status" -ne 0 || "$nested_frame_resource_probe_status" -ne 0 || "$resource_branch_join_probe_status" -ne 0 || "$rejected_borrow_write_status" -ne 1 || "$rejected_borrow_alias_status" -ne 1 || "$rejected_borrow_field_write_status" -ne 1 || "$rejected_borrow_field_alias_status" -ne 1 || "$rejected_borrow_nested_prefix_status" -ne 1 || "$rejected_borrow_four_nested_alias_status" -ne 1 || "$rejected_borrow_move_parent_status" -ne 1 || "$rejected_resource_use_after_move_status" -ne 1 || "$rejected_borrow_move_status" -ne 1 || "$rejected_borrow_escape_status" -ne 1 || "$rejected_borrow_call_status" -ne 1 || "$rejected_borrow_index_alias_status" -ne 1 || "$rejected_borrow_multi_index_alias_status" -ne 1 || "$rejected_borrow_call_alias_status" -ne 1 || "$rejected_resource_branch_move_status" -ne 1 || "$rejected_borrow_mutable_source_status" -ne 1 || "$rejected_borrow_nested_catch_status" -ne 1 || "$rejected_borrow_nested_match_status" -ne 1 || "$borrow_shared_probe_status" -ne 0 || "$borrow_mutable_probe_status" -ne 0 || "$borrow_lexical_scope_probe_status" -ne 0 || "$borrow_disjoint_fields_probe_status" -ne 0 || "$borrow_nested_disjoint_fields_probe_status" -ne 0 || "$borrow_four_nested_fields_probe_status" -ne 0 || "$borrow_move_disjoint_field_probe_status" -ne 0 || "$borrow_call_summary_probe_status" -ne 0 || "$borrow_indexed_places_probe_status" -ne 0 || "$borrow_multi_indexed_places_probe_status" -ne 0 || "$nested_frame_resource_probe_status" -ne 0 || "$resource_branch_join_probe_status" -ne 0 || "$rejected_borrow_write_probe_status" -ne 0 || "$rejected_borrow_alias_probe_status" -ne 0 || "$rejected_borrow_field_write_probe_status" -ne 0 || "$rejected_borrow_field_alias_probe_status" -ne 0 || "$rejected_borrow_nested_prefix_probe_status" -ne 0 || "$rejected_borrow_four_nested_alias_probe_status" -ne 0 || "$rejected_borrow_move_parent_probe_status" -ne 0 || "$rejected_resource_use_after_move_probe_status" -ne 0 || "$rejected_borrow_move_probe_status" -ne 0 || "$rejected_borrow_escape_probe_status" -ne 0 || "$rejected_borrow_call_probe_status" -ne 0 || "$rejected_borrow_index_alias_probe_status" -ne 0 || "$rejected_borrow_multi_index_alias_probe_status" -ne 0 || "$rejected_borrow_call_alias_probe_status" -ne 0 || "$rejected_resource_branch_move_probe_status" -ne 0 || "$rejected_borrow_mutable_source_probe_status" -ne 0 || "$rejected_borrow_nested_catch_probe_status" -ne 0 || "$rejected_borrow_nested_match_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: resource statuses shared=%s mutable=%s call_summary=%s branch_join=%s rejected_branch_move=%s probes call_summary=%s nested_frame=%s branch_join=%s rejected_call_alias=%s rejected_branch_move=%s\n' "$borrow_shared_status" "$borrow_mutable_status" "$borrow_call_summary_status" "$resource_branch_join_status" "$rejected_resource_branch_move_status" "$borrow_call_summary_probe_status" "$nested_frame_resource_probe_status" "$resource_branch_join_probe_status" "$rejected_borrow_call_alias_probe_status" "$rejected_resource_branch_move_probe_status" >&2
    exit 1
fi

if [[ "$rejected_checked_index_nested_status" -ne 1 ]]; then
    printf 'proof test matrix failed: checked index hid nested unchecked index (%s)\n' "$rejected_checked_index_nested_status" >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_checked_index_nested.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); repairs = report["repair_queue"]; assert [(item["rule"], item["failure"]["kind"]) for item in repairs] == [("index-lower", "index-lower-unproven"), ("index-upper", "index-upper-unproven")]; assert all(item["goal_id"] == item["failure"]["goal_id"] for item in repairs)'
checked_index_diagnostics_statuses=("${PIPESTATUS[@]}")
checked_index_diagnostics_status=${checked_index_diagnostics_statuses[0]}
checked_index_diagnostics_json_status=${checked_index_diagnostics_statuses[1]}
run_json_report "$ROOT_DIR/examples/rejected_call_multiple_preconditions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); repairs = [item for item in report["repair_queue"] if item["failure"]["kind"] == "call-requires-unproven"]; assert len(repairs) == 2; assert all(item["goal_id"] == item["failure"]["goal_id"] for item in repairs); assert repairs[0]["goal_id"] != repairs[1]["goal_id"]; assert report["replay"]["gaps"] == 0'
multiple_preconditions_statuses=("${PIPESTATUS[@]}")
multiple_preconditions_status=${multiple_preconditions_statuses[0]}
multiple_preconditions_json_status=${multiple_preconditions_statuses[1]}
run_json_report "$ROOT_DIR/examples/lexicographic_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["repair_queue"] == []; assert report["replay"]["gaps"] == 0'
lexicographic_repair_queue_statuses=("${PIPESTATUS[@]}")
lexicographic_repair_queue_status=${lexicographic_repair_queue_statuses[0]}
lexicographic_repair_queue_json_status=${lexicographic_repair_queue_statuses[1]}
run_json_report "$ROOT_DIR/examples/rejected_void_postcondition.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); repairs = report["repair_queue"]; assert len(repairs) == 1; assert repairs[0]["failure"]["kind"] == "ensure-unproven"; assert repairs[0]["goal_id"] == repairs[0]["failure"]["goal_id"]'
void_postcondition_goal_statuses=("${PIPESTATUS[@]}")
void_postcondition_goal_status=${void_postcondition_goal_statuses[0]}
void_postcondition_goal_json_status=${void_postcondition_goal_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --goal 3 "$ROOT_DIR/examples/rejected_checked_index_nested.elisa" | python3 -c 'import json, sys; goal = json.load(sys.stdin); assert goal["format"] == "elisa-proof-goal-v1"; assert goal["status"] == "unknown"; assert goal["goal_id"] == 3; assert goal["goal"]["rule"] == "index-upper"; assert goal["goal"]["proposition"]["operator"] == "<"; assert goal["failure"]["goal_id"] == 3; assert goal["source"]["complete"] is False; assert "kernel" not in goal'
focused_open_goal_statuses=("${PIPESTATUS[@]}")
focused_open_goal_status=${focused_open_goal_statuses[0]}
focused_open_goal_json_status=${focused_open_goal_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --goal 7 "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; goal = json.load(sys.stdin); assert goal["status"] == "proved"; assert goal["goal"]["replay_status"] == "replayed"; assert goal["failure"] is None; assert goal["source"]["complete"] is True'
focused_proved_goal_statuses=("${PIPESTATUS[@]}")
focused_proved_goal_status=${focused_proved_goal_statuses[0]}
focused_proved_goal_json_status=${focused_proved_goal_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --goal 999999 "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; goal = json.load(sys.stdin); assert goal["status"] == "not_found"; assert goal["goal"] is None; assert goal["failure"] is None'
focused_missing_goal_statuses=("${PIPESTATUS[@]}")
focused_missing_goal_status=${focused_missing_goal_statuses[0]}
focused_missing_goal_json_status=${focused_missing_goal_statuses[1]}
python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/goal_fingerprint_a.elisa" "$ROOT_DIR/examples/goal_fingerprint_b.elisa" <<'PY'
import json
import subprocess
import sys

first = json.loads(subprocess.check_output([sys.argv[1], "--goal", "1", sys.argv[2]]))
shifted = json.loads(subprocess.check_output([sys.argv[1], "--goal", "2", sys.argv[3]]))
assert first["goal_fingerprint"] == shifted["goal_fingerprint"]
assert first["goal"]["line"] != shifted["goal"]["line"]
PY
stable_goal_fingerprint_status=$?
"$ROOT_DIR/build/elisa-proof" --goal 4294967296 "$ROOT_DIR/examples/verified.elisa" >/dev/null
focused_overflow_goal_status=$?
"$ROOT_DIR/build/elisa-proof" --goal -1 "$ROOT_DIR/examples/verified.elisa" >/dev/null
focused_negative_goal_status=$?
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/lemma.elisa" | python3 -c 'import json, sys; catalog = json.load(sys.stdin); assert catalog["format"] == "elisa-proof-theorems-v1"; assert catalog["source"]["complete"] is True; assert [item["name"] for item in catalog["theorems"]] == ["nonnegative", "named_nonnegative"]; assert all(item["verified"] and item["signature_valid"] and item["proof_goals_valid"] and item["proof_replay_complete"] for item in catalog["theorems"]); assert all(theorem["proof_goals"] and all(goal["proven"] and goal["replayed"] and isinstance(goal["certificate_id"], int) for goal in theorem["proof_goals"]) for theorem in catalog["theorems"]); assert catalog["theorems"][0]["parameters"] == ["x"]; assert catalog["theorems"][0]["parameter_types"] == [{"kind": "ident", "name": "i64", "line": 1}]; assert [item["name"] for item in catalog["theorems"][1]["parameter_types"]] == ["i64", "i64"]; assert len(catalog["theorems"][1]["requires"]) == 2; assert len(catalog["theorems"][1]["ensures"]) == 1'
theorem_catalog_statuses=("${PIPESTATUS[@]}")
theorem_catalog_status=${theorem_catalog_statuses[0]}
theorem_catalog_json_status=${theorem_catalog_statuses[1]}
run_json_report "$ROOT_DIR/examples/lemma.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); traces = [trace for trace in report["kernel"]["fact_traces"] if trace["kind"] == "lemma-summary"]; assert report["status"] == "proved" and report["replay"]["gaps"] == 0; assert [trace["dependency"] for trace in traces] == ["nonnegative", "named_nonnegative"]; assert [len(trace["summary_bindings"]) for trace in traces] == [1, 2]; assert [len(trace["summary_require_goal_ids"]) for trace in traces] == [1, 2]; assert all(trace["summary_ensure_index"] == 0 for trace in traces); goals = report["goals"]; assert all(all(goals[goal_id]["proven"] and goals[goal_id]["replay_status"] == "replayed" for goal_id in trace["summary_require_goal_ids"]) for trace in traces)'
lemma_summary_provenance_statuses=("${PIPESTATUS[@]}")
lemma_summary_provenance_status=${lemma_summary_provenance_statuses[0]}
lemma_summary_provenance_json_status=${lemma_summary_provenance_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/rejected_lemma.elisa" | python3 -c 'import json, sys; catalog = json.load(sys.stdin); assert catalog["source"]["complete"] is False; assert len(catalog["theorems"]) == 1; theorem = catalog["theorems"][0]; assert theorem["name"] == "unsound"; assert theorem["verified"] is False; assert theorem["verification_reason"] == "body-unverified"; assert theorem["signature_valid"] is True; assert theorem["proof_goals_valid"] is True; assert theorem["proof_replay_complete"] is False; assert any(not goal["proven"] and goal["certificate_id"] is None and not goal["replayed"] for goal in theorem["proof_goals"])'
rejected_theorem_catalog_statuses=("${PIPESTATUS[@]}")
rejected_theorem_catalog_status=${rejected_theorem_catalog_statuses[0]}
rejected_theorem_catalog_json_status=${rejected_theorem_catalog_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/lemma_default_catalog.elisa" | python3 -c 'import json, sys; theorem = json.load(sys.stdin)["theorems"][0]; assert theorem["verified"] is True; assert theorem["parameters"] == ["x", "amount"]; assert theorem["parameter_defaults"] == [None, {"kind": "int", "value": 7}]'
default_theorem_catalog_statuses=("${PIPESTATUS[@]}")
default_theorem_catalog_status=${default_theorem_catalog_statuses[0]}
default_theorem_catalog_json_status=${default_theorem_catalog_statuses[1]}
