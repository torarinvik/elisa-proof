# shellcheck shell=bash
# Part 3 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
if [[ "$rejected_conditional_status" -ne 1 ]]; then
    printf 'proof test matrix failed: false conditional postcondition was accepted\n' >&2
    exit 1
fi

run_json_report "$ROOT_DIR/examples/implicit_structural_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
implicit_structural_status=${PIPESTATUS[1]}
if [[ "$implicit_structural_status" -ne 0 ]]; then
    printf 'proof test matrix failed: implicit structural termination\n' >&2
    exit 1
fi

run_json_report "$ROOT_DIR/examples/inferred_product_structural_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
inferred_product_structural_status=${PIPESTATUS[1]}
if [[ "$inferred_product_structural_status" -ne 0 ]]; then
    printf 'proof test matrix failed: inferred product structural termination\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/structural_shadowed_subterm.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
structural_shadowed_subterm_status=${PIPESTATUS[1]}
if [[ "$structural_shadowed_subterm_status" -ne 0 ]]; then
    printf 'proof test matrix failed: shadowed structural subterm identity\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_match_shadow_fact.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert not any(goal["proven"] for goal in report["goals"] if goal["rule"] != "resource-safety"); assert any(finding["kind"] == "proof-step-unproven" for finding in report["findings"])'
rejected_match_shadow_fact_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_match_shadow_fact_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: shadowed loop binder reused an outer proof fact\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/bounded_recursive_depth.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0'
bounded_recursive_depth_status=${PIPESTATUS[1]}
if [[ "$bounded_recursive_depth_status" -ne 0 ]]; then
    printf 'proof test matrix failed: bounded numeric recursive ranking\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_implicit_structural_decreases.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-implicit-structural.json"
rejected_implicit_structural_status=$?
if [[ "$rejected_implicit_structural_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nondecreasing implicit recursion was accepted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_inferred_product_structural_decreases.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-inferred-product-structural.json"
rejected_inferred_product_structural_status=$?
if [[ "$rejected_inferred_product_structural_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nondecreasing inferred product recursion was accepted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_bounded_recursive_depth.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-bounded-depth.json"
rejected_bounded_recursive_depth_status=$?
if [[ "$rejected_bounded_recursive_depth_status" -ne 1 ]]; then
    printf 'proof test matrix failed: unbounded numeric recursion was accepted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/nested_pure_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0'
nested_pure_call_status=${PIPESTATUS[1]}
if [[ "$nested_pure_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested certified-pure call expression\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/cast_not_index.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 2; assert report["replay"]["gaps"] == 0'
cast_not_index_status=${PIPESTATUS[1]}
if [[ "$cast_not_index_status" -ne 0 ]]; then
    printf 'proof test matrix failed: cast syntax treated as runtime indexing\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/early_return_index_guard.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
early_return_index_guard_probe_status=${PIPESTATUS[1]}
if [[ "$early_return_index_guard_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: early-return guard facts\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/loop_range_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(origin["kind"] == "loop-range" for goal in report["goals"] for origin in goal["fact_origins"] if origin); assert report["replay"]["gaps"] == 0'
loop_range_probe_status=${PIPESTATUS[1]}
if [[ "$loop_range_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: loop-derived collection bounds\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/for_invariant.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert any(origin and origin["kind"] == "loop-invariant" for goal in report["goals"] for origin in goal["fact_origins"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
for_invariant_probe_status=${PIPESTATUS[1]}
if [[ "$for_invariant_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: ordinary for-loop invariant was not preserved and replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_for_invariant.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert any(finding["kind"] == "invariant-not-preserved" and finding["status"] == "unknown" and not finding["counterexample_found"] for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_for_invariant_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_for_invariant_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: broken ordinary for-loop invariant was accepted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_for_invariant_scope.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert any(finding["kind"] == "loop-invariant-scope" and finding["status"] == "unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_for_invariant_scope_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_for_invariant_scope_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: out-of-scope for-loop invariant was accepted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/indexed_frame.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "index-lower" for goal in report["goals"]); assert any(goal["rule"] == "index-upper" for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
index_bounds_probe_status=${PIPESTATUS[1]}
if [[ "$index_bounds_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: indexed access bounds\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_index_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); lower = next(goal for goal in report["goals"] if goal["rule"] == "index-lower"); upper = next(goal for goal in report["goals"] if goal["rule"] == "index-upper"); assert lower["proven"] is True; assert any(origin and origin["kind"] == "type-bound" for origin in lower["fact_origins"]); assert upper["proven"] is False; assert report["status"] == "failed"'
unsigned_bound_probe_status=${PIPESTATUS[1]}
if [[ "$unsigned_bound_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler-backed unsigned lower bound\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_indexn_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert sum(finding["kind"] == "index-upper-unproven" for finding in report["findings"]) >= 2; assert report["replay"]["gaps"] == 0'
indexn_rejected_probe_status=${PIPESTATUS[1]}
if [[ "$indexn_rejected_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: unchecked multi-index dimensions were accepted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_pattern_or_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "pattern-unsupported" for finding in report["findings"]) or report["summary"]["semantic_errors"] > 0; assert report["replay"]["gaps"] == 0'
pattern_or_binding_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_or_binding_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: OR-pattern payload binding was accepted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pure_index_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; lower = next(goal for goal in report["goals"] if goal["rule"] == "index-lower"); assert lower["proven"] is True; assert any(origin and origin["kind"] == "type-bound" for origin in lower["fact_origins"]); assert report["replay"]["gaps"] == 0'
pure_index_call_probe_status=${PIPESTATUS[1]}
if [[ "$pure_index_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pure-call fact preservation\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/index_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]); assert any(origin and origin["dependency"] == "identity_index" for goal in report["goals"] for origin in goal["fact_origins"] if origin); assert report["replay"]["gaps"] == 0'
index_call_summary_probe_status=${PIPESTATUS[1]}
if [[ "$index_call_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exact pure index result summary\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/indexn_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert sum(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]) >= 2; assert report["replay"]["gaps"] == 0'
indexn_call_summary_probe_status=${PIPESTATUS[1]}
if [[ "$indexn_call_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exact pure multi-index result summaries\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/slice_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert {goal["rule"] for goal in report["goals"]} >= {"slice-lower", "slice-upper", "slice-order"}; assert report["replay"]["gaps"] == 0'
slice_call_summary_probe_status=${PIPESTATUS[1]}
if [[ "$slice_call_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exact pure slice endpoint summaries\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_index_pure_result.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(goal["rule"] == "index-upper" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
rejected_index_pure_result_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_index_pure_result_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pure index result did not retain its bound obligation\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/type_bound_state_flow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); lower = next(goal for goal in report["goals"] if goal["rule"] == "index-lower"); upper = next(goal for goal in report["goals"] if goal["rule"] == "index-upper"); assert report["status"] == "failed"; assert lower["proven"] is True; assert any(origin and origin["kind"] == "type-bound" for origin in lower["fact_origins"]); assert upper["proven"] is False; assert report["replay"]["gaps"] == 0'
type_bound_state_flow_probe_status=${PIPESTATUS[1]}
if [[ "$type_bound_state_flow_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: type-bound state-flow preservation\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_while_body_visibility.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "loop-invariant-missing" for finding in report["findings"]); assert any(goal["rule"] == "index-upper" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
while_body_visibility_probe_status=${PIPESTATUS[1]}
if [[ "$while_body_visibility_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: while-body obligation visibility\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_unverified_function_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "function-summary-unverified" for finding in report["findings"]); assert any(goal["name"] == "trusts_bad_claim" and not goal["proven"] for goal in report["goals"]); functions = [declaration for declaration in report["declaration_details"] if declaration["kind"] == "function"]; assert all(not declaration["verified"] for declaration in functions); assert functions[0]["verification_reason"] == "body-unverified"; assert functions[1]["verification_reason"] == "dependency-unverified"; assert report["replay"]["gaps"] == 0'
unverified_summary_probe_status=${PIPESTATUS[1]}
if [[ "$unverified_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: unverified executable summaries were trusted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_recursive_lemma.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "lemma-summary-unverified" for finding in report["findings"]); assert any(declaration["kind"] == "lemma" and not declaration["verified"] for declaration in report["declaration_details"]); assert any(declaration["name"] == "use_recursive_lemma" and declaration["verification_reason"] == "dependency-unverified" for declaration in report["declaration_details"]); assert report["replay"]["gaps"] == 0'
unverified_lemma_summary_probe_status=${PIPESTATUS[1]}
if [[ "$unverified_lemma_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: unverified lemma summaries were trusted\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/slice_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert {goal["rule"] for goal in report["goals"]} >= {"slice-lower", "slice-upper", "slice-order"}; assert report["replay"]["gaps"] == 0'
slice_bounds_probe_status=${PIPESTATUS[1]}
if [[ "$slice_bounds_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: slice endpoint bounds\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/fixed_array_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 6; assert all(goal["proven"] for goal in report["goals"] if goal["rule"] == "index-upper"); assert any(origin and origin["kind"] == "type-bound" for goal in report["goals"] for origin in goal["fact_origins"] if goal["rule"] == "index-upper"); assert report["replay"]["gaps"] == 0'
fixed_array_bounds_probe_status=${PIPESTATUS[1]}
if [[ "$fixed_array_bounds_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: fixed-array type bounds\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/fixed_array_fields.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 26; upper = [goal for goal in report["goals"] if goal["rule"] == "index-upper"]; assert len(upper) == 8 and all(goal["proven"] for goal in upper); assert all(any(origin and origin["kind"] == "global-constant" for origin in goal["fact_origins"]) for goal in upper); flag = [goal for goal in report["goals"] if goal["name"] == "live_flag" and goal["rule"] == "goal"]; assert len(flag) == 1 and flag[0]["proven"]; assert report["replay"]["gaps"] == 0'
fixed_array_fields_probe_status=${PIPESTATUS[1]}
if [[ "$fixed_array_fields_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: fixed-array struct-field and qualified-extent bounds\n' >&2
    exit 1
fi
rejected_fixed_array_fields_report="$standalone_probe_dir/rejected-fixed-array-fields.json"
run_json_report "$ROOT_DIR/examples/rejected_fixed_array_fields.elisa" >"$rejected_fixed_array_fields_report"
rejected_fixed_array_fields_status=$?
if [[ "$rejected_fixed_array_fields_status" -ne 1 ]] || ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1])); assert report["status"] == "failed"; found = sorted((finding["name"], finding["kind"]) for finding in report["findings"]); assert found == [("rejected_derived_extent", "expression-unsupported"), ("rejected_derived_flag", "contract-proposition-type"), ("rejected_flag", "ensure-unproven"), ("rejected_off_by_one", "index-upper-unproven")], found; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0' "$rejected_fixed_array_fields_report"; then
    printf 'proof test matrix failed: rejected_fixed_array_fields=%s\n' "$rejected_fixed_array_fields_status" >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/nested_call_kept_values.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 30; bounds = [goal for goal in report["goals"] if goal["rule"] in ("index-lower", "index-upper") and goal["name"] != "open"]; assert len(bounds) == 20 and all(goal["proven"] for goal in bounds); assert report["replay"]["gaps"] == 0'
nested_call_kept_values_probe_status=${PIPESTATUS[1]}
if [[ "$nested_call_kept_values_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: values a nested call cannot reach\n' >&2
    exit 1
fi
rejected_nested_call_kept_values_report="$standalone_probe_dir/rejected-nested-call-kept-values.json"
run_json_report "$ROOT_DIR/examples/rejected_nested_call_kept_values.elisa" >"$rejected_nested_call_kept_values_report"
rejected_nested_call_kept_values_status=$?
if [[ "$rejected_nested_call_kept_values_status" -ne 1 ]] || ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1])); assert report["status"] == "failed"; found = sorted((finding["line"], finding["name"], finding["kind"]) for finding in report["findings"]); assert found == [(24, "rejected_lent_copy", "index-upper-unproven"), (31, "rejected_lent_before", "index-upper-unproven"), (31, "rejected_lent_before", "index-upper-unproven"), (36, "rejected_written_field", "index-upper-unproven")], found; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0' "$rejected_nested_call_kept_values_report"; then
    printf 'proof test matrix failed: rejected_nested_call_kept_values=%s\n' "$rejected_nested_call_kept_values_status" >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/literal_index.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 18; bounds = [goal for goal in report["goals"] if goal["rule"] in ("index-lower", "index-upper")]; assert len(bounds) == 10 and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in bounds); assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []'
literal_index_probe_status=${PIPESTATUS[1]}
if [[ "$literal_index_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a literal-bound local was not indexed through its literal\n' >&2
    exit 1
fi
rejected_literal_index_report="$standalone_probe_dir/rejected-literal-index.json"
run_json_report "$ROOT_DIR/examples/rejected_literal_index.elisa" >"$rejected_literal_index_report"
rejected_literal_index_status=$?
if [[ "$rejected_literal_index_status" -ne 1 ]] || ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1])); assert report["status"] == "failed"; found = sorted((finding["line"], finding["name"], finding["kind"]) for finding in report["findings"]); assert found == [(8, "unguarded", "index-upper-unproven"), (14, "off_by_one", "index-upper-unproven"), (21, "other_literal", "index-upper-unproven"), (28, "rebound", "index-upper-unproven"), (38, "lent_after_guard", "index-upper-unproven")], found; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0' "$rejected_literal_index_report"; then
    printf 'proof test matrix failed: rejected_literal_index=%s\n' "$rejected_literal_index_status" >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/disjunctive_goals.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 13; ensures = [goal for goal in report["goals"] if goal["rule"] == "goal"]; assert sorted(goal["name"] for goal in ensures) == ["chained_order", "implied", "implied_bound", "live"]; bounds = [goal for goal in report["goals"] if goal["name"] == "live_then_read" and goal["rule"] in ("index-lower", "index-upper")]; assert len(bounds) == 2; assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in ensures + bounds); assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []'
disjunctive_goals_probe_status=${PIPESTATUS[1]}
if [[ "$disjunctive_goals_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a disjunctive goal was not proved through the negated left disjunct\n' >&2
    exit 1
fi
rejected_disjunctive_goals_report="$standalone_probe_dir/rejected-disjunctive-goals.json"
run_json_report "$ROOT_DIR/examples/rejected_disjunctive_goals.elisa" >"$rejected_disjunctive_goals_report"
rejected_disjunctive_goals_status=$?
if [[ "$rejected_disjunctive_goals_status" -ne 1 ]] || ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1])); assert report["status"] == "failed"; found = sorted((finding["line"], finding["name"], finding["kind"]) for finding in report["findings"]); assert found == [(8, "rejected_either", "ensure-unproven"), (12, "rejected_bound", "ensure-unproven"), (16, "rejected_wrong_side", "ensure-unproven")], found; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0' "$rejected_disjunctive_goals_report"; then
    printf 'proof test matrix failed: rejected_disjunctive_goals=%s\n' "$rejected_disjunctive_goals_status" >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/leaving_branch_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 24; ensures = [goal for goal in report["goals"] if goal["rule"] == "goal"]; assert sorted(set(goal["name"] for goal in ensures)) == ["leaving_branch_call", "live", "match_leaving_arm_call", "returning_branch_call"]; guarded = ["block_guard", "bound_guard", "match_leaving_arm", "postfix_guard"]; bounds = [goal for goal in report["goals"] if goal["name"] in guarded and goal["rule"] in ("index-lower", "index-upper")]; assert sorted(set(goal["name"] for goal in bounds)) == guarded; assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in ensures + bounds); assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []'
leaving_branch_join_probe_status=${PIPESTATUS[1]}
if [[ "$leaving_branch_join_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a branch that leaves weakened the join after it\n' >&2
    exit 1
fi
rejected_leaving_branch_join_report="$standalone_probe_dir/rejected-leaving-branch-join.json"
run_json_report "$ROOT_DIR/examples/rejected_leaving_branch_join.elisa" >"$rejected_leaving_branch_join_report"
rejected_leaving_branch_join_status=$?
if [[ "$rejected_leaving_branch_join_status" -ne 1 ]] || ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1])); assert report["status"] == "failed"; found = sorted((finding["line"], finding["name"], finding["kind"]) for finding in report["findings"]); assert found == [(25, "inverted_guard", "index-upper-unproven"), (34, "falling_branch_call", "ensure-unproven"), (40, "condition_call", "ensure-unproven"), (50, "scrutinee_call", "ensure-unproven"), (60, "match_falling_arm_call", "ensure-unproven")], found; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0' "$rejected_leaving_branch_join_report"; then
    printf 'proof test matrix failed: rejected_leaving_branch_join=%s\n' "$rejected_leaving_branch_join_status" >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pass_statement.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 19; ensures = [goal for goal in report["goals"] if goal["rule"] == "goal"]; assert sorted(set(goal["name"] for goal in ensures)) == ["branch_pass", "call_condition_pass", "call_scrutinee_pass", "lemma_pass", "loop_pass", "match_arm_pass", "proof_block_pass", "pure_helper_pass"]; assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in ensures); details = {detail["name"]: detail for detail in report["declaration_details"]}; assert details["helper"]["pure"] and details["helper"]["verified"]; assert details["lemma_pass"]["verified"]; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []'
pass_statement_probe_status=${PIPESTATUS[1]}
if [[ "$pass_statement_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pass did not keep the facts and purity it passes through\n' >&2
    exit 1
fi
rejected_pass_statement_report="$standalone_probe_dir/rejected-pass-statement.json"
run_json_report "$ROOT_DIR/examples/rejected_pass_statement.elisa" >"$rejected_pass_statement_report"
rejected_pass_statement_status=$?
if [[ "$rejected_pass_statement_status" -ne 1 ]] || ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1])); assert report["status"] == "failed"; found = sorted((finding["line"], finding["name"], finding["kind"]) for finding in report["findings"]); assert found == [(20, "false_after_pass", "ensure-unproven"), (24, "hole_in_body", "proof-hole"), (30, "hole_in_branch", "proof-hole"), (36, "hole_in_lemma", "proof-hole"), (42, "hole_in_proof_block", "proof-hole"), (47, "dropped_prefix_block", "expression-unsupported")], found; details = {detail["name"]: detail for detail in report["declaration_details"]}; assert not any(details[name]["verified"] for name in ["false_after_pass", "hole_in_body", "hole_in_branch", "hole_in_lemma", "hole_in_proof_block", "dropped_prefix_block"]); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0' "$rejected_pass_statement_report"; then
    printf 'proof test matrix failed: rejected_pass_statement=%s\n' "$rejected_pass_statement_status" >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/counting_loop_measure.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 27 and report["summary"]["proven"] == 27; ensures = [goal for goal in report["goals"] if goal["rule"] == "goal"]; assert sorted(set(goal["name"] for goal in ensures)) == ["count_up_signed", "count_up_unsigned", "rebind_beside_peer", "shared_names_cancel", "transposed_difference", "unsigned_gap", "within_the_term_budget"]; assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in report["goals"]); assert report["findings"] == []; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0 and report["replay"]["replayed"] == 27; assert report["trust"]["trusted_assumptions"] == []'
counting_loop_measure_probe_status=${PIPESTATUS[1]}
if [[ "$counting_loop_measure_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: cancellation did not prove the counting-loop measures\n' >&2
    exit 1
fi
rejected_counting_loop_measure_report="$standalone_probe_dir/rejected-counting-loop-measure.json"
run_json_report "$ROOT_DIR/examples/rejected_counting_loop_measure.elisa" >"$rejected_counting_loop_measure_report"
rejected_counting_loop_measure_status=$?
if [[ "$rejected_counting_loop_measure_status" -ne 1 ]] || ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1])); assert report["status"] == "failed"; found = sorted((finding["line"], finding["name"], finding["kind"]) for finding in report["findings"]); assert found == [(9, "flipped_descent", "loop-decreases-unproven"), (9, "flipped_descent", "loop-decreases-unproven"), (9, "flipped_descent", "loop-decreases-unproven"), (14, "flipped_descent", "ensure-unproven"), (20, "unguarded_cancellation", "ensure-unproven"), (26, "doubled_name", "ensure-unproven"), (32, "wrong_step", "ensure-unproven"), (39, "rebind_without_peer", "ensure-unproven")], found; assert not any(goal["proven"] for goal in report["goals"] if goal["rule"] == "goal" and goal["line"] not in (9, 47)); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0' "$rejected_counting_loop_measure_report"; then
    printf 'proof test matrix failed: rejected_counting_loop_measure=%s\n' "$rejected_counting_loop_measure_status" >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/dogfood_kernel_core.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"]=="proved" and r["verification_state"]=="proved"; assert r["summary"]["proven"]==50 and r["summary"]["obligations"]==50; assert r["findings"]==[] and r["summary"]["declarations"]>=9; assert r["replay"]["gaps"]==0; assert [g["goal_id"] for g in r["goals"]]==list(range(len(r["goals"]))); assert [c["certificate_id"] for c in r["certificates"]]==list(range(len(r["certificates"]))); assert all(g["certificate_id"] is not None and g["certificate_id"]<len(r["certificates"]) for g in r["goals"])'
dogfood_core_contract_probe_status=${PIPESTATUS[1]}
if [[ "$dogfood_core_contract_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: direct calls to dogfood kernel contracts\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/src/proof/kernel_core.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"]=="proved" and r["verification_state"]=="proved"; assert r["summary"]["proven"]==37 and r["summary"]["obligations"]==37; assert r["findings"]==[] and r["summary"]["semantic_errors"]==0; assert r["replay"]["gaps"]==0 and r["kernel"]["independent_replay"] is True'
kernel_core_self_probe_status=${PIPESTATUS[1]}
if [[ "$kernel_core_self_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: kernel core does not verify itself\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/rejected_kernel_arena_cycle.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] != "proved"; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] for goal in report["goals"]); assert any(not goal["proven"] for goal in report["goals"]); assert any(finding["kind"] == "function-summary-unverified" and finding["name"] == "rejected_cycle_arena" for finding in report["findings"])'
arena_cycle_probe_status=${PIPESTATUS[1]}
if [[ "$arena_cycle_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: cyclic source-neutral arena was not rejected fail-closed\n' >&2
    exit 1
fi
for malformed_proposition_fixture in rejected_nonbool_hypothesis_reuse rejected_nonbool_opaque_propositions; do
    malformed_proposition_report="$standalone_probe_dir/$malformed_proposition_fixture.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$malformed_proposition_fixture.elisa" >"$malformed_proposition_report"
    malformed_proposition_status=$?
    set -e
    if [[ "$malformed_proposition_status" -ne 1 ]]; then
        printf 'proof test matrix failed: non-Boolean source proposition was accepted in %s\n' "$malformed_proposition_fixture" >&2
        exit 1
    fi
    # Stage1's sound compiler gate may also reject the malformed logical operator
    # directly; the proof-specific proposition-formation finding must still be present.
    python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "failed"; assert any(f["kind"] == "contract-proposition-type" for f in r["findings"]); assert r["replay"]["gaps"] == 0 and r["replay"]["certificates"] == r["replay"]["replayed"]; assert not any(g["proven"] and g["rule"] != "resource-safety" for g in r["goals"]); assert all(not d["verified"] for d in r["declaration_details"] if d["kind"] == "function" and d["name"].startswith("rejected_"))' "$malformed_proposition_report"
done
optional_result_report="$standalone_probe_dir/rejected-optional-result-comparison.json"
optional_semantic_report="$standalone_probe_dir/rejected-optional-result-semantic.txt"
set +e
if elisa_compiler_is_stage0 "$SELF_HOST_COMPILER"; then
    "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit semantic "$ROOT_DIR/examples/rejected_optional_result_comparison.elisa" >"$optional_semantic_report" 2>&1
    optional_semantic_status=$?
    optional_semantic_diagnostic='cannot compare i64? and i64'
else
    # Stage1 deliberately exposes semantic diagnostics through its normal compile gate,
    # not stage0's `-emit semantic` report mode. Compile the invalid contract directly and
    # require the semantic gate to reject it before backend body-decline recovery.
    "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-optional-result-comparison.o" "$ROOT_DIR/examples/rejected_optional_result_comparison.elisa" >"$optional_semantic_report" 2>&1
    optional_semantic_status=$?
    optional_semantic_diagnostic='cannot compare'
fi
set -e
if [[ "$optional_semantic_status" -eq 0 ]] || ! grep -F -q -- "$optional_semantic_diagnostic" "$optional_semantic_report"; then
    printf 'proof test matrix failed: optional payload comparison was not rejected by the frontend\n' >&2
    if [[ -s "$optional_semantic_report" ]]; then
        printf 'compiler output for the rejected-optional-result probe:\n' >&2
        cat "$optional_semantic_report" >&2
    fi
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_optional_result_comparison.elisa" >"$optional_result_report"
optional_result_status=$?
set -e
if [[ "$optional_result_status" -ne 1 ]]; then
    printf 'proof test matrix failed: ill-typed optional proposition authorized a proof\n' >&2
    exit 1
fi
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); fs=r["findings"]; ds=[d for d in r["declaration_details"] if d["kind"]=="function"]; assert r["status"]=="failed" and r["replay"]["gaps"]==0 and r["replay"]["certificates"]==r["replay"]["replayed"]; assert any(f["kind"]=="contract-proposition-type" and f["name"]=="rejected_optional_result_comparison" for f in fs); assert any(f["kind"]=="function-summary-unverified" and f["name"]=="rejected_optional_getelse_summary" for f in fs); assert all(not d["verified"] for d in ds); assert not any(dep["kind"]=="function-summary" and dep["name"]=="rejected_optional_result_comparison" for g in r["goals"] for dep in g["dependencies"])' "$optional_result_report"
optional_repair_report="$standalone_probe_dir/rejected-optional-result-repair.json"
set +e
"$ROOT_DIR/build/elisa-proof" --repair-all "$ROOT_DIR/examples/rejected_optional_result_comparison.elisa" >"$optional_repair_report"
optional_repair_status=$?
set -e
if [[ "$optional_repair_status" -ne 1 ]]; then
    printf 'proof test matrix failed: malformed optional source repair result status changed unexpectedly\n' >&2
    exit 1
fi
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"]=="inadmissible" and r["source"]["admissible"] is False; assert any(g["name"]=="rejected_optional_getelse_summary" and g["status"]=="unrepaired" and g["tried"]==0 for g in r["goals"])' "$optional_repair_report"
optional_target_tactic_report="$standalone_probe_dir/rejected-optional-result-target-tactic.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_malformed_source_target.json" "$ROOT_DIR/examples/rejected_optional_result_comparison.elisa" >"$optional_target_tactic_report"
optional_target_tactic_status=$?
set -e
if [[ "$optional_target_tactic_status" -ne 1 ]]; then
    printf 'proof test matrix failed: source-bound tactic admitted a malformed proposition goal\n' >&2
    exit 1
fi
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"]=="failed" and r["source"]["status"]=="failed" and r["source"]["admissible"] is False; assert r["source_goal_binding"]["bound"] is True and r["source_goal_binding"]["goal_id"]==2; assert r["tactic"]["certificate_replayed"] is False' "$optional_target_tactic_report"
optional_valid_target_report="$standalone_probe_dir/rejected-optional-result-valid-target-tactic.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_malformed_source_valid_target.json" "$ROOT_DIR/examples/rejected_optional_result_comparison.elisa" >"$optional_valid_target_report"
optional_valid_target_status=$?
set -e
if [[ "$optional_valid_target_status" -ne 1 ]]; then
    printf 'proof test matrix failed: a valid localized target bypassed malformed source admission\n' >&2
    exit 1
fi
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"]=="failed" and r["source"]["admissible"] is False; assert r["source_goal_binding"]["bound"] is True and r["source_goal_binding"]["goal_id"]==1; assert r["tactic"]["certificate_replayed"] is True and r["tactic"]["status"]=="proved"' "$optional_valid_target_report"
shadowed_float_alias_report="$standalone_probe_dir/rejected-builtin-float-alias.json"
set +e
run_json_report "$ROOT_DIR/examples/rejected_builtin_float_alias.elisa" >"$shadowed_float_alias_report"
shadowed_float_alias_status=$?
set -e
if [[ "$shadowed_float_alias_status" -ne 1 ]]; then
    printf 'proof test matrix failed: a floating alias reusing a primitive spelling was accepted\n' >&2
    exit 1
fi
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "failed" and r["summary"]["semantic_errors"] > 0; d=next(d for d in r["declaration_details"] if d["name"] == "rejected_builtin_float_alias_reflexivity"); assert not d["verified"] and d["verification_reason"] == "body-unverified"; assert not any(g["name"] == d["name"] and g["proven"] and g["rule"] == "goal" for g in r["goals"]); assert all(q["failure"]["kind"] == "ensure-unproven" for q in r["repair_queue"])' "$shadowed_float_alias_report"
float_mode_report="$standalone_probe_dir/float-opaque-guard.json"
run_json_report "$ROOT_DIR/examples/float_opaque_guard.elisa" >"$float_mode_report"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "proved" and r["findings"] == []; v={d["name"]: d["verified"] for d in r["declaration_details"]}; assert v["float_scale"] and v["float_normalize_x"] and v["float_guarded_pair"]' "$float_mode_report"
for float_probe in rejected_float_le_guard rejected_float_nan_order; do
    float_probe_report="$standalone_probe_dir/$float_probe.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$float_probe.elisa" >"$float_probe_report"
    float_probe_status=$?
    set -e
    if [[ "$float_probe_status" -ne 1 ]]; then
        printf 'proof test matrix failed: float mode accepted %s\n' "$float_probe" >&2
        exit 1
    fi
done
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert [(f["name"], f["kind"]) for f in r["findings"]] == [("float_normalize_le", "call-requires-unproven")]' "$standalone_probe_dir/rejected_float_le_guard.json"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert sorted(f["name"] for f in r["findings"] if f["kind"] == "ensure-unproven") == ["float_not_self_unequal", "float_trichotomy"]; assert not any(g["proven"] for g in r["goals"] if g["rule"] == "goal")' "$standalone_probe_dir/rejected_float_nan_order.json"
unsigned_alias_rejection_report="$standalone_probe_dir/rejected-unsigned-alias.json"
set +e
run_json_report "$ROOT_DIR/examples/rejected_unsigned_alias.elisa" >"$unsigned_alias_rejection_report"
unsigned_alias_rejection_status=$?
set -e
if [[ "$unsigned_alias_rejection_status" -ne 1 ]]; then
    printf 'proof test matrix failed: overflowing unsigned alias obligation was not rejected\n' >&2
    exit 1
fi
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); kinds={f["kind"] for f in r["findings"]}; assert r["status"] == "failed" and r["summary"]["semantic_errors"] == 0; assert "contract-proposition-type" not in kinds and "ensure-unproven" in kinds; assert r["replay"]["gaps"] == 0 and r["replay"]["certificates"] == r["replay"]["replayed"]' "$unsigned_alias_rejection_report"
run_json_report "$ROOT_DIR/examples/boolean_opaque_propositions.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "proved" and r["summary"]["failed"] == 0; assert r["replay"]["gaps"] == 0 and r["replay"]["certificates"] == r["replay"]["replayed"]; assert not r["findings"]'
boolean_proposition_probe_status=${PIPESTATUS[1]}
if [[ "$boolean_proposition_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: valid Boolean opaque propositions did not replay\n' >&2
    exit 1
fi
for typed_proposition_fixture in kernel_named_container_call enum_variant_proposition; do
    run_json_report "$ROOT_DIR/examples/$typed_proposition_fixture.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); expected={"kernel_named_container_call":"valid_call", "enum_variant_proposition":"variant_tag_is_proposition"}[sys.argv[1]]; assert r["status"] == "proved" and r["summary"]["failed"] == 0; assert r["replay"]["gaps"] == 0 and r["replay"]["certificates"] == r["replay"]["replayed"]; assert not r["findings"]; assert any(d["kind"] == "function" and d["name"] == expected and d["verified"] for d in r["declaration_details"])' "$typed_proposition_fixture"
    typed_proposition_status=${PIPESTATUS[1]}
    if [[ "$typed_proposition_status" -ne 0 ]]; then
        printf 'proof test matrix failed: typed positive proposition fixture %s\n' "$typed_proposition_fixture" >&2
        exit 1
    fi
done
assertion_proposition_report="$standalone_probe_dir/rejected-nonbool-assert.json"
set +e
run_json_report "$ROOT_DIR/examples/rejected_nonbool_assert_call.elisa" >"$assertion_proposition_report"
assertion_proposition_status=$?
set -e
if [[ "$assertion_proposition_status" -ne 1 ]]; then
    printf 'proof test matrix failed: non-Boolean assert produced an admitted proof\n' >&2
    exit 1
fi
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "failed" and r["summary"]["semantic_errors"] > 0; assert any(f["kind"] == "contract-proposition-type" for f in r["findings"]); assert not any(g["rule"] == "proof-step" and g["proven"] for g in r["goals"]); f=next(d for d in r["declaration_details"] if d["name"] == "rejected_nonbool_assert_call"); assert not f["verified"] and f["verification_reason"] == "body-unverified"; assert r["replay"]["gaps"] == 0' "$assertion_proposition_report"
# An inadmissible source is never repaired, so the batch exits 1 as well.
set +e
"$ROOT_DIR/build/elisa-proof" --repair-all "$ROOT_DIR/examples/rejected_nonbool_hypothesis_reuse.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "inadmissible" and r["source"]["admissible"] is False and r["summary"]["repaired"] == 0 and all(g["script"] is None for g in r["goals"])'
repair_proposition_probe_statuses=("${PIPESTATUS[@]}")
set -e
repair_proposition_probe_status=${repair_proposition_probe_statuses[1]}
[[ "${repair_proposition_probe_statuses[0]}" -eq 1 ]] || repair_proposition_probe_status=1
if [[ "$repair_proposition_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: malformed source contracts entered the repair queue\n' >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_quantifier.json" "$ROOT_DIR/examples/rejected_nonbool_hypothesis_reuse.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "failed" and r["source"]["status"] == "failed"; assert r["source_goal_binding"]["bound"] is False; assert r["tactic"]["status"] == "proved" and r["tactic"]["valid"] is True'
portable_proposition_tactic_statuses=("${PIPESTATUS[@]}")
set -e
if [[ "${portable_proposition_tactic_statuses[0]}" -ne 1 || "${portable_proposition_tactic_statuses[1]}" -ne 0 ]]; then
    printf 'proof test matrix failed: portable tactic proof was bound to an ill-formed source proposition\n' >&2
    exit 1
fi
control_proposition_report="$standalone_probe_dir/rejected-nonbool-control.json"
set +e
run_json_report "$ROOT_DIR/examples/rejected_nonbool_control_condition.elisa" >"$control_proposition_report"
control_proposition_status=$?
set -e
if [[ "$control_proposition_status" -ne 1 ]]; then
    printf 'proof test matrix failed: a non-Boolean control guard was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "failed" and r["summary"]["semantic_errors"] > 0; assert any(f["kind"] == "contract-proposition-type" and f["line"] == 8 for f in r["findings"]); assert any(f["kind"] == "contract-proposition-type" and f["name"] == "rejected_void_comparison_if_condition" for f in r["findings"]); for_name={d["name"]:d for d in r["declaration_details"] if d["kind"] == "function"}; assert all(not for_name[n]["verified"] and for_name[n]["verification_reason"] == "body-unverified" for n in ("rejected_nonbool_if_condition", "rejected_void_comparison_if_condition")); assert r["replay"]["gaps"] == 0' "$control_proposition_report"; then
    printf 'proof test matrix failed: non-Boolean control proposition was reported as verified\n' >&2
    exit 1
fi
kernel_core_repeat_a="$(mktemp)"
kernel_core_repeat_b="$(mktemp)"
TEST_CLEANUP+=("$kernel_core_repeat_a" "$kernel_core_repeat_b")
run_json_report "$ROOT_DIR/src/proof/kernel_core.elisa" >"$kernel_core_repeat_a"
run_json_report "$ROOT_DIR/src/proof/kernel_core.elisa" >"$kernel_core_repeat_b"
if ! cmp -s "$kernel_core_repeat_a" "$kernel_core_repeat_b"; then
    printf 'proof test matrix failed: repeated kernel reports are not byte-identical\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/bitwise_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0'
bitwise_probe_status=${PIPESTATUS[1]}
if [[ "$bitwise_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: fixed-width bitwise kernel coverage\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/proof_step_derivation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert any(trace["kind"] == "proof-step" and trace["premises_count"] > 0 for trace in report["kernel"]["fact_traces"]); assert report["replay"]["gaps"] == 0'
proof_trace_probe_status=${PIPESTATUS[1]}
if [[ "$proof_trace_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: derived proof-step provenance\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/function_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "identity_nonnegative" for goal in report["goals"] for dependency in goal["dependencies"]); assert any(dependency["kind"] == "function-summary" and dependency["name"] == "identity_nonnegative" for certificate in report["certificates"] for dependency in certificate["dependencies"]); index = next(item for item in report["dependency_index"] if item["name"] == "identity_nonnegative"); assert index["goal_ids"]; assert [item["name"] for item in report["declaration_details"]] == ["identity_nonnegative", "caller_uses_summary"]; assert report["declaration_details"][0]["parameters"] == ["x"]; assert report["declaration_details"][1]["requires"] == 1 and report["declaration_details"][1]["ensures"] == 1; assert report["replay"]["gaps"] == 0'
dependency_probe_status=${PIPESTATUS[1]}
if [[ "$dependency_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: explicit theorem dependency metadata\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pattern_proof.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; assert any(origin["kind"] == "branch-condition" for certificate in report["certificates"] for origin in certificate["fact_origins"]); assert any(fact.get("operator") in ("==", ">=") for certificate in report["certificates"] for fact in certificate["facts"])'
pattern_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: ADT/pattern branch facts\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/total_match.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0'
total_match_probe_status=${PIPESTATUS[1]}
if [[ "$total_match_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: total returning match\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_frame_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["status"] == "disproved" for finding in report["findings"])'
disproved_probe_statuses=("${PIPESTATUS[@]}")
set -e
disproved_probe_status=${disproved_probe_statuses[1]}
if [[ "$disproved_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: disproved finding classification\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_counterexample.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); findings = [finding for finding in report["findings"] if finding["kind"] == "ensure-unproven"]; repair = report["repair_queue"]; semantic = report["semantic_diagnostics"]; assert report["verification_state"] == "disproved"; assert len(semantic) == report["summary"]["semantic_diagnostics"]; assert any(item["severity"] == 1 and item["kind_code"] > 0 and item["message"] for item in semantic); assert any(finding["status"] == "disproved" and finding["counterexample_found"] and finding["counterexample"] and finding["counterexample"][0]["operator"] == "==" and finding["counterexample"][0]["left"].get("name") == "x" and finding["counterexample"][0]["right"].get("value") == 0 and finding["goal_id"] == repair[0]["goal_id"] for finding in findings); assert repair and repair[0]["failure"]["status"] == "disproved" and repair[0]["failure"]["counterexample_found"] and repair[0]["failure"]["goal_id"] == repair[0]["goal_id"]'
counterexample_probe_statuses=("${PIPESTATUS[@]}")
set -e
counterexample_probe_status=${counterexample_probe_statuses[1]}
if [[ "$counterexample_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: deterministic counterexample witness\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/counterexample_domain.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; findings = {finding["name"]: finding for finding in report["findings"]}; exact = findings["exact_scalar_counterexample"]; wrapped = findings["narrow_wrap_is_not_a_counterexample"]; assert exact["status"] == "disproved" and exact["counterexample_found"] and exact["counterexample"][0]["right"]["value"] == 0; assert wrapped["status"] == "unknown" and not wrapped["counterexample_found"] and wrapped["counterexample"] == []'
counterexample_domain_status=${PIPESTATUS[1]}
set -e
if [[ "$counterexample_domain_status" -ne 0 ]]; then
    printf 'proof test matrix failed: width-inexact model emitted a false counterexample\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/counterexample_boolean_domains.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["replay"]["gaps"] == 0; findings = {finding["name"]: finding for finding in report["findings"] if finding["kind"] == "ensure-unproven"}; boolean = findings["boolean_parameter_counterexample"]; anchored_boolean = findings["boolean_equality_counterexample"]; ambiguous_boolean = findings["ambiguous_boolean_equality"]; ambiguous_character = findings["ambiguous_character_equality"]; assert boolean["status"] == "disproved" and boolean["counterexample_found"]; assert boolean["counterexample"] and boolean["counterexample"][0]["right"]["kind"] == "bool" and boolean["counterexample"][0]["right"]["value"] is True; assert anchored_boolean["status"] == "disproved" and anchored_boolean["counterexample_found"] and anchored_boolean["counterexample"][0]["right"]["kind"] == "bool"; assert ambiguous_boolean["status"] == "unknown" and not ambiguous_boolean["counterexample_found"] and ambiguous_boolean["counterexample"] == []; assert ambiguous_character["status"] == "unknown" and not ambiguous_character["counterexample_found"] and ambiguous_character["counterexample"] == []'
counterexample_boolean_domains_status=${PIPESTATUS[1]}
set -e
if [[ "$counterexample_boolean_domains_status" -ne 0 ]]; then
    printf 'proof test matrix failed: counterexample models must preserve or refuse scalar domains\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_inexact_overloaded_counterexample.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert any(f["name"] == "always_equal_contract" and f["status"] == "unknown" and not f["counterexample_found"] for f in report["findings"])'
overloaded_counterexample_status=${PIPESTATUS[1]}
set -e
if [[ "$overloaded_counterexample_status" -ne 0 ]]; then
    printf 'proof test matrix failed: overloaded equality was evaluated with built-in counterexample semantics\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_signed_overflow_model.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed" and report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0 and report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}; assert not functions["signed_increment_is_strict"]["verified"]; assert functions["signed_increment_is_strict_when_safe"]["verified"]; assert any(f["name"] == "signed_increment_is_strict" and f["status"] == "unknown" and not f["counterexample_found"] for f in report["findings"])'
signed_overflow_model_status=${PIPESTATUS[1]}
set -e
if [[ "$signed_overflow_model_status" -ne 0 ]]; then
    printf 'proof test matrix failed: signed machine-integer overflow was proved using mathematical arithmetic\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/signed_overflow_bounded_model.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed" and report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0 and report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}; assert functions["signed_square_bounded_safe"]["verified"]; assert not functions["signed_square_wraps_in_model_domain"]["verified"]; assert any(f["name"] == "signed_square_wraps_in_model_domain" and f["status"] == "unknown" and not f["counterexample_found"] for f in report["findings"])'
signed_overflow_bounded_model_status=${PIPESTATUS[1]}
set -e
if [[ "$signed_overflow_bounded_model_status" -ne 0 ]]; then
    printf 'proof test matrix failed: bounded models must refuse fixed-width overflow domains\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_dogfood_kernel_core.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert [goal["goal_id"] for goal in report["goals"]] == list(range(len(report["goals"]))); assert [certificate["certificate_id"] for certificate in report["certificates"]] == list(range(len(report["certificates"]))); assert any(goal["certificate_id"] is None and not goal["proven"] for goal in report["goals"]); assert any(finding["kind"] == "ensure-unproven" and finding["status"] == "unknown" for finding in report["findings"])'
dogfood_kernel_core_probe_statuses=("${PIPESTATUS[@]}")
if [[ "${dogfood_kernel_core_probe_statuses[0]}" -ne 1 || "${dogfood_kernel_core_probe_statuses[1]}" -ne 0 ]]; then
    printf 'proof test matrix failed: rejected kernel-core fixture pipeline returned unexpected statuses\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/verified.elisa" >/dev/null
verified_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/bounded_model.elisa" >/dev/null
bounded_model_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/dogfood_kernel.elisa" >/dev/null
dogfood_kernel_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/dogfood_kernel_core.elisa" >/dev/null
dogfood_kernel_core_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_dogfood_kernel_core.elisa" >/dev/null
rejected_dogfood_kernel_core_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/replay_constant.elisa" >/dev/null
replay_constant_status=$?
if [[ "$replay_constant_status" -ne 0 ]]; then
    printf 'proof test matrix failed: replay_constant=%s\n' "$replay_constant_status" >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/move_runtime_value.elisa" >/dev/null
move_runtime_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_shared_read.elisa" >/dev/null
borrow_shared_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_mutable_write.elisa" >/dev/null
borrow_mutable_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_lexical_scope.elisa" >/dev/null
borrow_lexical_scope_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_disjoint_fields.elisa" >/dev/null
borrow_disjoint_fields_status=$?
