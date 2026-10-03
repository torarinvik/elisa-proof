# shellcheck shell=bash
# Part 2 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
for replay_fixture in replay_constant loop_accumulator arithmetic_identity equality_alias congruence summary_swapped_arguments quantifier collection_quantifier quantifier_structural_terms expression_witness call_stable_facts shared_borrow_calls writable_lend_calls region_lend_calls region_call_summary condition_call_positions product_sign frame_lifetime difference_constraints disjunctive_facts modulo_division_bounds proof_step_derivation pattern_proof pattern_or pinned_pattern pattern_scalar_literals total_match value_match value_match_nested_pure_call bounded_model loop_range_facts for_invariant for_loop_control_invariant indexed_frame slice_bounds indexn_kernel indexn_call_summary pure_index_call index_call_summary slice_call_summary fixed_array_bounds fixed_array_fields nested_call_kept_values literal_index disjunctive_goals leaving_branch_join pass_statement counting_loop_measure fixed_array_slice_bounds checked_index_fallback getelse_recovery getelse_checked_index getelse_call getelse_loop_control getelse_raise catch_expression catch_nested_pure_arm_call loop_control_invariant continue_decreases continue_decreases_branch shorthand_member constructor_kernel dogfood_kernel region_allocation region_statement region_auto_close region_new_call_argument region_new_mutable_call_argument unsigned_alias resource_nested_scalar_call body_ensures contract_placement replay_qualified_constant_argument conditional_join; do
    run_json_report "$ROOT_DIR/examples/$replay_fixture.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0'
    replay_probe_status=$?
    if [[ "$replay_probe_status" -ne 0 ]]; then
        printf 'proof test matrix failed: replay coverage for %s\n' "$replay_fixture" >&2
        exit 1
    fi
done
run_json_report "$ROOT_DIR/examples/region_allocation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-open" in kinds and "resource-region-alloc" in kinds and "resource-region-bind" in kinds and "resource-region-alloc-discard" in kinds and "resource-region-close" in kinds'
region_allocation_probe_status=${PIPESTATUS[1]}
if [[ "$region_allocation_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: new[r] allocation/binding/discard transitions were not replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_generic_allocation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-param" in kinds and "resource-region-return-alloc" in kinds and "resource-region-return" in kinds and "resource-call-region" in kinds and "resource-call-result" in kinds'
region_generic_probe_status=${PIPESTATUS[1]}
if [[ "$region_generic_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic new[r] call/result was not replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_new_call_argument.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-call-alloc" in kinds and any(node["kind"] == "resource-call-arg" and node["operator"] == "region-new" for node in report["kernel"]["nodes"])'
region_new_call_probe_status=${PIPESTATUS[1]}
if [[ "$region_new_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: direct new[r] call temporary was not independently replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_new_mutable_call_argument.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-region-call-alloc" for node in report["kernel"]["nodes"])'
region_new_mutable_call_probe_status=${PIPESTATUS[1]}
if [[ "$region_new_mutable_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: mutable new[r] call temporary was not independently replayed\n' >&2
    exit 1
fi
set +e
rejected_region_new_return_report="$standalone_probe_dir/rejected-region-new-return.json"
run_json_report "$ROOT_DIR/examples/rejected_region_new_return_argument.elisa" >"$rejected_region_new_return_report"
rejected_region_new_return_status=$?
set -e
if [[ "$rejected_region_new_return_status" -ne 1 ]]; then
    printf 'proof test matrix failed: new[r] temporary escaped through a reference return\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "borrow-escape" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_region_new_return_report"; then
    printf 'proof test matrix failed: region temporary escape report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_reference_return_alias_report="$standalone_probe_dir/rejected-reference-return-alias.json"
run_json_report "$ROOT_DIR/examples/rejected_reference_return_alias.elisa" >"$rejected_reference_return_alias_report"
rejected_reference_return_alias_status=$?
set -e
if [[ "$rejected_reference_return_alias_status" -ne 1 ]]; then
    printf 'proof test matrix failed: reference-return alias was accepted as an independent capability\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "resource-use-after-move" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_reference_return_alias_report"; then
    printf 'proof test matrix failed: reference-return alias report was incomplete\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_statement.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert kinds.count("resource-region-open") == 1 and kinds.count("resource-region-close") == 1 and "resource-region-alloc" in kinds and "resource-region-bind" in kinds and "resource-region-alloc-discard" in kinds'
region_statement_probe_status=${PIPESTATUS[1]}
if [[ "$region_statement_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: canonical region statement transitions were not replayed\n' >&2
    exit 1
fi
set +e
rejected_region_duplicate_alias_report="$standalone_probe_dir/rejected-region-duplicate-alias.json"
run_json_report "$ROOT_DIR/examples/rejected_region_duplicate_mutable_alias.elisa" >"$rejected_region_duplicate_alias_report"
rejected_region_duplicate_alias_status=$?
set -e
if [[ "$rejected_region_duplicate_alias_status" -ne 1 ]]; then
    printf 'proof test matrix failed: duplicate mutable region alias was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "region-alias-unsupported" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_region_duplicate_alias_report"; then
    printf 'proof test matrix failed: duplicate mutable region alias report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_region_assign_duplicate_owner_report="$standalone_probe_dir/rejected-region-assign-duplicate-owner.json"
run_json_report "$ROOT_DIR/examples/rejected_region_assign_duplicate_owner.elisa" >"$rejected_region_assign_duplicate_owner_report"
rejected_region_assign_duplicate_owner_status=$?
set -e
if [[ "$rejected_region_assign_duplicate_owner_status" -ne 1 ]]; then
    printf 'proof test matrix failed: duplicate mutable region owner assignment was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "resource-use-after-move" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_region_assign_duplicate_owner_report"; then
    printf 'proof test matrix failed: duplicate mutable region owner assignment report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_region_bind_mutable_external_report="$standalone_probe_dir/rejected-region-bind-mutable-external.json"
run_json_report "$ROOT_DIR/examples/rejected_region_bind_mutable_external.elisa" >"$rejected_region_bind_mutable_external_report"
rejected_region_bind_mutable_external_status=$?
set -e
if [[ "$rejected_region_bind_mutable_external_status" -ne 1 ]]; then
    printf 'proof test matrix failed: mutable external region alias was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "region-alias-unsupported" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_region_bind_mutable_external_report"; then
    printf 'proof test matrix failed: mutable external region alias report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_negative_affine_difference_report="$standalone_probe_dir/rejected-negative-affine-difference.json"
run_json_report "$ROOT_DIR/examples/rejected_negative_affine_difference.elisa" >"$rejected_negative_affine_difference_report"
rejected_negative_affine_difference_status=$?
set -e
if [[ "$rejected_negative_affine_difference_status" -ne 1 ]]; then
    printf 'proof test matrix failed: signed affine difference admitted a false postcondition\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "ensure-unproven" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_negative_affine_difference_report"; then
    printf 'proof test matrix failed: signed affine difference report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_negative_affine_goal_report="$standalone_probe_dir/rejected-negative-affine-goal.json"
run_json_report "$ROOT_DIR/examples/rejected_negative_affine_goal.elisa" >"$rejected_negative_affine_goal_report"
rejected_negative_affine_goal_status=$?
set -e
if [[ "$rejected_negative_affine_goal_status" -ne 1 ]]; then
    printf 'proof test matrix failed: signed affine goal admitted a false postcondition\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "ensure-unproven" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_negative_affine_goal_report"; then
    printf 'proof test matrix failed: signed affine goal report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_borrow_call_duplicate_alias_report="$standalone_probe_dir/rejected-borrow-call-duplicate-alias.json"
run_json_report "$ROOT_DIR/examples/rejected_borrow_call_duplicate_alias.elisa" >"$rejected_borrow_call_duplicate_alias_report"
rejected_borrow_call_duplicate_alias_status=$?
set -e
if [[ "$rejected_borrow_call_duplicate_alias_status" -ne 1 ]]; then
    printf 'proof test matrix failed: duplicate mutable call alias was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "borrow-call-alias" and f["status"] == "unknown" for f in report["findings"]); assert not any(node["kind"] == "resource-call" and node["name"] == "write_pair" for node in report["kernel"]["nodes"]); assert report["replay"]["gaps"] == 0' "$rejected_borrow_call_duplicate_alias_report"; then
    printf 'proof test matrix failed: duplicate mutable call alias report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_unsigned_overflow_goal_report="$standalone_probe_dir/rejected-unsigned-overflow-goal.json"
run_json_report "$ROOT_DIR/examples/rejected_unsigned_overflow_goal.elisa" >"$rejected_unsigned_overflow_goal_report"
rejected_unsigned_overflow_goal_status=$?
set -e
if [[ "$rejected_unsigned_overflow_goal_status" -ne 1 ]]; then
    printf 'proof test matrix failed: unsigned overflow postcondition was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "ensure-unproven" and f["status"] == "unknown" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_unsigned_overflow_goal_report"; then
    printf 'proof test matrix failed: unsigned overflow report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_overloaded_primitive_rewrite_report="$standalone_probe_dir/rejected-overloaded-primitive-rewrite.json"
run_json_report "$ROOT_DIR/examples/rejected_overloaded_primitive_rewrite.elisa" >"$rejected_overloaded_primitive_rewrite_report"
rejected_overloaded_primitive_rewrite_status=$?
set -e
if [[ "$rejected_overloaded_primitive_rewrite_status" -ne 1 ]]; then
    printf 'proof test matrix failed: overloaded primitive equality was accepted as Leibniz equality\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "ensure-unproven" and f["status"] == "unknown" for f in report["findings"]); assert any(f["kind"] == "expression-unsupported" for f in report["findings"]); assert not any(goal["rule"] == "goal" and goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0' "$rejected_overloaded_primitive_rewrite_report"; then
    printf 'proof test matrix failed: overloaded primitive equality report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_overloaded_primitive_global_rewrite_report="$standalone_probe_dir/rejected-overloaded-primitive-global-rewrite.json"
run_json_report "$ROOT_DIR/examples/rejected_overloaded_primitive_global_rewrite.elisa" >"$rejected_overloaded_primitive_global_rewrite_report"
rejected_overloaded_primitive_global_rewrite_status=$?
set -e
if [[ "$rejected_overloaded_primitive_global_rewrite_status" -ne 1 ]]; then
    printf 'proof test matrix failed: overloaded global primitive equality was accepted as Leibniz equality\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "ensure-unproven" and f["status"] == "unknown" for f in report["findings"]); assert any(f["kind"] == "expression-unsupported" for f in report["findings"]); assert not any(goal["rule"] == "goal" and goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0' "$rejected_overloaded_primitive_global_rewrite_report"; then
    printf 'proof test matrix failed: overloaded global primitive equality report was incomplete\n' >&2
    exit 1
fi
for overloaded_literal_fixture in rejected_overloaded_literal_equality rejected_overloaded_literal_fact rejected_overloaded_literal_rewrite; do
    overloaded_literal_report="$standalone_probe_dir/$overloaded_literal_fixture.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$overloaded_literal_fixture.elisa" >"$overloaded_literal_report"
    overloaded_literal_status=$?
    set -e
    if [[ "$overloaded_literal_status" -ne 1 ]]; then
        printf 'proof test matrix failed: source-overloaded literal semantics were accepted for %s\n' "$overloaded_literal_fixture" >&2
        exit 1
    fi
    if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert report["verification_state"] in ("unknown", "unsupported"); assert any(f["kind"] == "ensure-unproven" and f["status"] in ("unknown", "unsupported") for f in report["findings"]); assert not any(goal["rule"] == "goal" and goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0' "$overloaded_literal_report"; then
        printf 'proof test matrix failed: source-overloaded literal report was incomplete for %s\n' "$overloaded_literal_fixture" >&2
        exit 1
    fi
done
set +e
rejected_overloaded_runtime_assert_report="$standalone_probe_dir/rejected-overloaded-runtime-assert.json"
run_json_report "$ROOT_DIR/examples/rejected_overloaded_runtime_assert.elisa" >"$rejected_overloaded_runtime_assert_report"
rejected_overloaded_runtime_assert_status=$?
set -e
if [[ "$rejected_overloaded_runtime_assert_status" -ne 1 ]]; then
    printf 'proof test matrix failed: overloaded runtime assertion fact was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert report["verification_state"] in ("unknown", "unsupported"); assert any(f["kind"] == "ensure-unproven" and f["status"] in ("unknown", "unsupported") for f in report["findings"]); assert not any(goal["rule"] == "goal" and goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0' "$rejected_overloaded_runtime_assert_report"; then
    printf 'proof test matrix failed: overloaded runtime assertion report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_overloaded_literal_simp_report="$standalone_probe_dir/rejected-overloaded-literal-simp.json"
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_rejected_overloaded_literal_equality.json" "$ROOT_DIR/examples/rejected_overloaded_literal_equality.elisa" >"$rejected_overloaded_literal_simp_report"
rejected_overloaded_literal_simp_status=$?
set -e
if [[ "$rejected_overloaded_literal_simp_status" -ne 1 ]]; then
    printf 'proof test matrix failed: source-bound simp accepted an overloaded literal operator\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); tactic=report["tactic"]; assert report["status"] == "failed"; assert tactic["valid"] is False and tactic["solved"] is False; assert tactic["action_count"] == 0' "$rejected_overloaded_literal_simp_report"; then
    printf 'proof test matrix failed: overloaded literal simp rejection report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_overloaded_literal_have_report="$standalone_probe_dir/rejected-overloaded-literal-have.json"
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_rejected_overloaded_literal_fact.json" "$ROOT_DIR/examples/rejected_overloaded_literal_fact.elisa" >"$rejected_overloaded_literal_have_report"
rejected_overloaded_literal_have_status=$?
set -e
if [[ "$rejected_overloaded_literal_have_status" -ne 1 ]]; then
    printf 'proof test matrix failed: source-bound have accepted an overloaded literal operator\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); tactic=report["tactic"]; assert report["status"] == "failed"; assert tactic["valid"] is False and tactic["solved"] is False; assert tactic["action_count"] == 0' "$rejected_overloaded_literal_have_report"; then
    printf 'proof test matrix failed: overloaded literal have rejection report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_overloaded_literal_rewrite_report="$standalone_probe_dir/rejected-overloaded-literal-rewrite.json"
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_rejected_overloaded_literal_rewrite.json" "$ROOT_DIR/examples/rejected_overloaded_literal_rewrite.elisa" >"$rejected_overloaded_literal_rewrite_report"
rejected_overloaded_literal_rewrite_status=$?
set -e
if [[ "$rejected_overloaded_literal_rewrite_status" -ne 1 ]]; then
    printf 'proof test matrix failed: source-bound rewrite used overloaded literal equality\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); tactic=report["tactic"]; assert report["status"] == "failed"; assert tactic["valid"] is False and tactic["solved"] is False; assert tactic["action_count"] == 0; assert tactic["accepted_count"] == 0; assert tactic["certificate_replayed"] is False' "$rejected_overloaded_literal_rewrite_report"; then
    printf 'proof test matrix failed: overloaded literal rewrite rejection report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_overloaded_literal_decide_report="$standalone_probe_dir/rejected-overloaded-literal-decide.json"
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_rejected_overloaded_literal_decide.json" "$ROOT_DIR/examples/rejected_overloaded_literal_equality.elisa" >"$rejected_overloaded_literal_decide_report"
rejected_overloaded_literal_decide_status=$?
set -e
if [[ "$rejected_overloaded_literal_decide_status" -ne 1 ]]; then
    printf 'proof test matrix failed: source-bound decide accepted an overloaded literal operator\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); tactic=report["tactic"]; assert report["status"] == "failed"; assert tactic["valid"] is False and tactic["solved"] is False; assert tactic["action_count"] == 0' "$rejected_overloaded_literal_decide_report"; then
    printf 'proof test matrix failed: overloaded literal decide rejection report was incomplete\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/unsigned_constant_in_range.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0'
unsigned_constant_in_range_probe_status=${PIPESTATUS[1]}
if [[ "$unsigned_constant_in_range_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: in-range unsigned constant arithmetic lost completeness\n' >&2
    exit 1
fi
for unsigned_constant_fixture in rejected_unsigned_constant_overflow rejected_unsigned_local_constant_overflow; do
    unsigned_constant_report="$standalone_probe_dir/$unsigned_constant_fixture.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$unsigned_constant_fixture.elisa" >"$unsigned_constant_report"
    unsigned_constant_status=$?
    set -e
    if [[ "$unsigned_constant_status" -ne 1 ]]; then
        printf 'proof test matrix failed: wrapping unsigned constant arithmetic was accepted for %s\n' "$unsigned_constant_fixture" >&2
        exit 1
    fi
    if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] >= 0; assert any(f["kind"] == "ensure-unproven" for f in report["findings"]); assert report["replay"]["gaps"] == 0; assert not any(goal["rule"] != "resource-safety" and goal["proven"] for goal in report["goals"])' "$unsigned_constant_report"; then
        printf 'proof test matrix failed: wrapping unsigned constant report was incomplete for %s\n' "$unsigned_constant_fixture" >&2
        exit 1
    fi
done
for unsigned_place_fixture in rejected_unsigned_field_overflow rejected_unsigned_element_overflow rejected_unsigned_field_width_congruence rejected_unsigned_element_width_congruence rejected_unsigned_nested_element_width_congruence rejected_unsigned_condition_width_inference; do
    unsigned_place_report="$standalone_probe_dir/$unsigned_place_fixture.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$unsigned_place_fixture.elisa" >"$unsigned_place_report"
    unsigned_place_status=$?
    set -e
    if [[ "$unsigned_place_status" -ne 1 ]]; then
        printf 'proof test matrix failed: wrapping arithmetic over an unsigned place was accepted for %s\n' "$unsigned_place_fixture" >&2
        exit 1
    fi
    if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "ensure-unproven" and f["status"] == "unknown" for f in report["findings"]); assert report["replay"]["gaps"] == 0; assert not any(goal["rule"] == "goal" and goal["proven"] for goal in report["goals"])' "$unsigned_place_report"; then
        printf 'proof test matrix failed: unsigned-place overflow report was incomplete for %s\n' "$unsigned_place_fixture" >&2
        exit 1
    fi
done
run_json_report "$ROOT_DIR/examples/unsigned_field_increment_bound.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0'
unsigned_field_increment_probe_status=${PIPESTATUS[1]}
if [[ "$unsigned_field_increment_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an in-range unsigned field increment lost its relational proof\n' >&2
    exit 1
fi
set +e
rejected_region_call_result_duplicate_owner_report="$standalone_probe_dir/rejected-region-call-result-duplicate-owner.json"
run_json_report "$ROOT_DIR/examples/rejected_region_call_result_duplicate_owner.elisa" >"$rejected_region_call_result_duplicate_owner_report"
rejected_region_call_result_duplicate_owner_status=$?
set -e
if [[ "$rejected_region_call_result_duplicate_owner_status" -ne 1 ]]; then
    printf 'proof test matrix failed: duplicate mutable owner through a call result was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "resource-use-after-move" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_region_call_result_duplicate_owner_report"; then
    printf 'proof test matrix failed: duplicate mutable owner through a call result report was incomplete\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_auto_close.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert kinds.count("resource-region-open") == 1 and kinds.count("resource-region-close") == 1'
region_auto_close_probe_status=${PIPESTATUS[1]}
if [[ "$region_auto_close_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: implicit region close was not replayed\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_region_use_after_destroy.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-region-use.json"
rejected_region_use_status=$?
set -e
if [[ "$rejected_region_use_status" -ne 1 ]]; then
    printf 'proof test matrix failed: use after destroy was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-region-use.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-use-after-destroy" for f in report["findings"]) or report["summary"]["semantic_errors"] > 0; assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: rejected region use report was incomplete\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_sview_after_region_destroy.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-sview-region-use.json"
rejected_sview_region_use_status=$?
set -e
if [[ "$rejected_sview_region_use_status" -ne 1 ]]; then
    printf 'proof test matrix failed: sview use after backing-region destruction was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-sview-region-use.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-use-after-destroy" or f["kind"] == "region-destroy-live-borrow" for f in report["findings"]); assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: rejected sview lifetime report was incomplete\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_sview_destroy_while_live.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-sview-live-destroy.json"
rejected_sview_live_destroy_status=$?
set -e
if [[ "$rejected_sview_live_destroy_status" -ne 1 ]]; then
    printf 'proof test matrix failed: backing region was destroyed while an sview remained live\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-sview-live-destroy.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-destroy-live-borrow" for f in report["findings"]); assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: live sview destroy report was incomplete\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/sview_region_live_use.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["gaps"] == 0'
run_json_report "$ROOT_DIR/examples/sview_region_reference_parameter.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["gaps"] == 0'
run_json_report "$ROOT_DIR/examples/sview_region_return_parameter.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0'
run_json_report "$ROOT_DIR/examples/sview_region_value_parameter.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0'
run_json_report "$ROOT_DIR/examples/sview_call_return_provenance.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0; assert report["replay"]["gaps"] == 0'
set +e
run_json_report "$ROOT_DIR/examples/rejected_sview_call_return_wrong_provenance.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-sview-call-provenance.json"
rejected_sview_call_provenance_status=$?
set -e
if [[ "$rejected_sview_call_provenance_status" -ne 1 ]]; then
    printf '%s\n' 'proof test matrix failed: a write to the sview backing argument was accepted' >&2
    exit 1
fi
# Compiler 2678ff10 itself rejects the read of `view` after `second.push` (semantic error 341).
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-sview-call-provenance.json")); assert report["status"] == "failed"; assert report["verification_state"] == "disproved"; semantic=[(d["kind_code"], d["line"], d["name"], d["expected"]) for d in report.get("semantic_diagnostics", []) if d["severity"] == 1]; assert semantic == [(341, 18, "view", "second")], semantic; assert report["summary"]["semantic_errors"] == 1; assert any(f["kind"] == "borrow-write-conflict" and f["status"] == "disproved" for f in report["findings"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'; then
    printf '%s\n' 'proof test matrix failed: call-return provenance was not replayed to the actual backing argument' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/reference_call_return_provenance.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0; assert report["replay"]["gaps"] == 0; nodes=report["kernel"]["nodes"]; assert any(n["kind"] == "resource-region-return" and n["operator"] == "param-call" and n["secondary_name"] == "second" for n in nodes)'
set +e
run_json_report "$ROOT_DIR/examples/rejected_reference_call_return_wrong_provenance.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-reference-call-provenance.json"
rejected_reference_call_provenance_status=$?
set -e
if [[ "$rejected_reference_call_provenance_status" -ne 1 ]] || ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-reference-call-provenance.json")); assert report["status"] == "failed"; assert report["verification_state"] == "disproved"; assert report["summary"]["semantic_errors"] == 0; assert any(f["kind"] == "resource-use-after-move" and f["status"] == "disproved" and f["line"] == 16 for f in report["findings"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'; then
    printf '%s\n' 'proof test matrix failed: a write to the reference call-return backing argument was accepted' >&2
    exit 1
fi
# Wrong-region, mutability-upgrade and branch-dependent call returns must be refused.
run_json_report "$ROOT_DIR/examples/regionless_reference_call_return_provenance.elisa" | python3 -c 'import json, sys; report=json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0; assert report["replay"]["gaps"] == 0; nodes=report["kernel"]["nodes"]; assert any(n["kind"] == "resource-region-return" and n["operator"] == "param-call" and n["name"] == "" and n["secondary_name"] == "b" for n in nodes)'
for rejected_call_return in rejected_regionless_reference_return_mutability_upgrade:region-return-witness-unsupported rejected_reference_call_return_region_mismatch:region-return-escape rejected_reference_call_return_mutability_upgrade:region-return-witness-unsupported rejected_nested_reference_return_provenance:region-return-witness-unsupported rejected_nested_sview_return_provenance:region-return-witness-unsupported; do
    rejected_call_return_example="${rejected_call_return%%:*}"
    rejected_call_return_kind="${rejected_call_return##*:}"
    # Compiler 2678ff10 itself rejects the read of `view` after `a.push` (semantic error 341).
    rejected_call_return_semantic=""
    [[ "$rejected_call_return_example" == rejected_nested_sview_return_provenance ]] && rejected_call_return_semantic="341:19:view:a"
    set +e
    run_json_report "$ROOT_DIR/examples/$rejected_call_return_example.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-call-return.json"
    rejected_call_return_status=$?
    set -e
    if [[ "$rejected_call_return_status" -ne 1 ]] || ! REJECTED_KIND="$rejected_call_return_kind" REJECTED_SEMANTIC="$rejected_call_return_semantic" python3 -c 'import json, os; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-call-return.json")); assert report["status"] == "failed"; assert report["verification_state"] != "proved"; semantic=[":".join(map(str, (d["kind_code"], d["line"], d["name"], d["expected"]))) for d in report.get("semantic_diagnostics", []) if d["severity"] == 1]; assert semantic == [d for d in [os.environ["REJECTED_SEMANTIC"]] if d], semantic; assert report["summary"]["semantic_errors"] == len(semantic); assert any(f["kind"] == os.environ["REJECTED_KIND"] for f in report["findings"]); assert report["replay"]["gaps"] == 0'; then
        printf 'proof test matrix failed: %s was not refused with %s\n' "$rejected_call_return_example" "$rejected_call_return_kind" >&2
        exit 1
    fi
done
set +e
run_json_report "$ROOT_DIR/examples/rejected_sview_return_after_region_destroy.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-sview-return-destroy.json"
rejected_sview_return_destroy_status=$?
set -e
if [[ "$rejected_sview_return_destroy_status" -ne 1 ]]; then
    printf 'proof test matrix failed: sview returned through a helper outlived its backing region\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-sview-return-destroy.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-destroy-live-borrow" or f["kind"] == "region-use-after-destroy" for f in report["findings"]); assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: helper-returned sview lifetime report was incomplete\n' >&2
    exit 1
fi
for sview_escape_fixture in rejected_sview_alias_region_escape rejected_sview_aggregate_region_escape; do
    set +e
    run_json_report "$ROOT_DIR/examples/$sview_escape_fixture.elisa" >"$ELISA_TEST_TMP/elisa-proof-$sview_escape_fixture.json"
    sview_escape_status=$?
    set -e
    if [[ "$sview_escape_status" -ne 1 ]]; then
        printf 'proof test matrix failed: sview lifetime escaped through %s\n' "$sview_escape_fixture" >&2
        exit 1
    fi
    if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "region-alias-unsupported" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$ELISA_TEST_TMP/elisa-proof-$sview_escape_fixture.json"; then
        printf 'proof test matrix failed: sview escape report was incomplete for %s\n' "$sview_escape_fixture" >&2
        exit 1
    fi
done
set +e
run_json_report "$ROOT_DIR/examples/rejected_sview_region_reference_write.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-sview-reference-write.json"
rejected_sview_reference_write_status=$?
set -e
if [[ "$rejected_sview_reference_write_status" -ne 1 ]]; then
    printf 'proof test matrix failed: write through the mutable backing reference was accepted while an sview was live\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-sview-reference-write.json")); assert report["status"] == "failed"; assert any(f["kind"] in {"borrow-write-conflict", "borrow-overlap-unproven"} for f in report["findings"]) or report["summary"]["semantic_errors"] > 0; assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: rejected sview-backed write report was incomplete\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_sview_region_parameter_write.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-sview-parameter-write.json"
rejected_sview_parameter_write_status=$?
set -e
if [[ "$rejected_sview_parameter_write_status" -ne 1 ]]; then
    printf 'proof test matrix failed: write in a region borrowed by an sview parameter was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-sview-parameter-write.json")); assert report["status"] == "failed"; assert any(f["kind"] in {"borrow-write-conflict", "borrow-overlap-unproven"} for f in report["findings"]); assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: rejected sview parameter write report was incomplete\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_region_call_binding_mismatch.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-region-call-binding.json"
rejected_region_call_binding_status=$?
set -e
if [[ "$rejected_region_call_binding_status" -ne 1 ]]; then
    printf 'proof test matrix failed: a returned reference changed its backing region at binding\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-region-call-binding.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-alias-unsupported" for f in report["findings"]) or report["summary"]["semantic_errors"] > 0; assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: mismatched reference result lifetime report was incomplete\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_region_generic_unmapped.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-region-generic.json"
rejected_region_generic_status=$?
set -e
if [[ "$rejected_region_generic_status" -ne 1 ]]; then
    printf 'proof test matrix failed: unmapped region-polymorphic call was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-region-generic.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-call-opaque" for f in report["findings"]); assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: unmapped region-polymorphic call report was incomplete\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_region_destroy_nested_without_binding.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-nested-region-destroy.json"
rejected_nested_region_destroy_status=$?
set -e
if [[ "$rejected_nested_region_destroy_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nested inherited-region destruction was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open(__import__("os").environ["ELISA_TEST_TMP"] + "/elisa-proof-rejected-nested-region-destroy.json")); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; assert any(f["kind"] == "region-destroy-unsupported" for f in report["findings"]) or report["summary"]["semantic_errors"] > 0'; then
    printf 'proof test matrix failed: nested inherited-region destruction report was incomplete\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pattern_scalar_literals.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "char" for node in report["kernel"]["nodes"])'
pattern_scalar_literals_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_scalar_literals_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: scalar literal pattern facts\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pinned_pattern.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] and goal["rule"] == "goal" for goal in report["goals"])'
pinned_pattern_probe_status=${PIPESTATUS[1]}
if [[ "$pinned_pattern_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pinned-pattern equality fact\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pattern_or.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] and goal["rule"] == "goal" for goal in report["goals"])'
pattern_or_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_or_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: closed OR-pattern branch fact\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/shorthand_member.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "shorthand" and node["name"] == "None" for node in report["kernel"]["nodes"])'
shorthand_member_probe_status=${PIPESTATUS[1]}
if [[ "$shorthand_member_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: const-enum shorthand was not encoded as a replayed kernel atom\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/constructor_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert "construct" in kinds; assert "record-update" in kinds; assert "field-init" in kinds'
constructor_kernel_probe_status=${PIPESTATUS[1]}
if [[ "$constructor_kernel_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: constructor/update terms were not encoded for independent replay\n' >&2
    exit 1
fi
# The source-neutral formation boundary rejects aggregate slice comparisons before lowering;
# keep all eight original assertions visible as failed formation obligations, not silently dropped.
set +e
run_json_report "$ROOT_DIR/examples/slice_kernel.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); fs=r["findings"]; assert r["status"]=="failed" and r["summary"]["semantic_errors"]==0 and r["summary"]["obligations"]==8; assert r["goals"]==[] and r["certificates"]==[] and r["replay"]["certificates"]==r["replay"]["replayed"]==0 and r["replay"]["gaps"]==0; assert len(fs)==8 and all(f["kind"]=="contract-proposition-type" and f["name"]=="slice_reflexive" for f in fs); assert {f["line"] for f in fs}==set(range(7,15)); assert r["kernel"]["nodes"]==[]'
slice_kernel_probe_status=${PIPESTATUS[1]}
set -e
if [[ "$slice_kernel_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: slice terms were not encoded for independent replay\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/indexn_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 8; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert sum(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]) >= 2; assert any(node["kind"] == "index-n" and node["children_count"] == 2 for node in report["kernel"]["nodes"])'
indexn_kernel_probe_status=${PIPESTATUS[1]}
if [[ "$indexn_kernel_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: bounded multi-index terms were not checked and replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/quantifier_structural_terms.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 6; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert {"quantifier", "array", "if"} <= kinds; assert "construct" not in kinds'
quantifier_structural_probe_status=${PIPESTATUS[1]}
if [[ "$quantifier_structural_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: structured quantifier substitution was not replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/checked_index_fallback.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert any(goal["rule"] == "checked-index" and goal["proven"] for goal in report["goals"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
checked_index_certificate_probe_status=${PIPESTATUS[1]}
if [[ "$checked_index_certificate_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: checked-index safety certificate was not replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/getelse_recovery.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 4; assert any(goal["rule"] == "checked-get" and goal["proven"] for goal in report["goals"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
getelse_recovery_probe_status=${PIPESTATUS[1]}
if [[ "$getelse_recovery_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: get-else control recovery was not independently checked\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/getelse_checked_index.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "checked-get" and goal["proven"] for goal in report["goals"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
getelse_checked_index_probe_status=${PIPESTATUS[1]}
if [[ "$getelse_checked_index_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: checked-get safety certificate was not replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/getelse_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "maybe_value" for goal in report["goals"] for dependency in goal["dependencies"]); assert report["replay"]["gaps"] == 0'
getelse_call_probe_status=${PIPESTATUS[1]}
if [[ "$getelse_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: get-else guarded call summary was not applied\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/catch_expression.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 7; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "catch_probe_value" for goal in report["goals"] for dependency in goal["dependencies"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
catch_expression_probe_status=${PIPESTATUS[1]}
if [[ "$catch_expression_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: expression catch success/error paths were not checked independently\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/continue_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
continue_decreases_probe_status=${PIPESTATUS[1]}
if [[ "$continue_decreases_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: straight-line continue decreases path was not checked\n' >&2
    exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_getelse_recovery.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "disproved"; assert any(finding["kind"] == "getelse-recovery-nonterminating" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_getelse_recovery_probe_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_getelse_recovery_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: falling-through get-else recovery was not rejected\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/conditional_proof.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 6; assert report["summary"]["proven"] == 6; assert report["replay"]["gaps"] == 0'
conditional_probe_status=${PIPESTATUS[1]}
if [[ "$conditional_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: conditional postcondition case elimination\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_conditional_proof.elisa" >"$ELISA_TEST_TMP/elisa-proof-rejected-conditional.json"
rejected_conditional_status=$?
