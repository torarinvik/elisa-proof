#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT_DIR/scripts/build.sh"

set +e
SELF_HOST_COMPILER="${ELISA_COMPILER_BIN:-}"
if [[ -z "$SELF_HOST_COMPILER" ]]; then
    # `elisac` was a symlink to the Go compiler and is gone; the stage names are
    # explicit now. Prefer the self-hosted compiler. The probe below only checks
    # compilation, so it deliberately uses the object mode shared by both stages.
    for candidate in elisac-stage1 elisac-stage0 elisac; do
        SELF_HOST_COMPILER="$(command -v "$candidate" 2>/dev/null || true)"
        [[ -n "$SELF_HOST_COMPILER" ]] && break
    done
fi
standalone_probe_dir="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-test.XXXXXX")"
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/kernel-replay-standalone.o" "$ROOT_DIR/examples/kernel_replay_standalone.elisa" >/dev/null 2>&1
kernel_replay_standalone_status=$?
if [[ "$kernel_replay_standalone_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-neutral replay module is not standalone-compilable\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/region-allocation.o" "$ROOT_DIR/examples/region_allocation.elisa" >/dev/null 2>&1
region_allocation_compiler_status=$?
if [[ "$region_allocation_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected valid new[r] allocation\n' >&2
    exit 1
fi
if [[ "$(basename "$SELF_HOST_COMPILER")" == "elisac-stage1" ]]; then
    "$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/region-generic-allocation.o" "$ROOT_DIR/examples/region_generic_allocation.elisa" >/dev/null 2>&1
    region_generic_compiler_status=$?
    if [[ "$region_generic_compiler_status" -ne 0 ]]; then
        printf 'proof test matrix failed: stage1 rejected region-polymorphic new[r] allocation\n' >&2
        exit 1
    fi
    "$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/region-new-call.o" "$ROOT_DIR/examples/region_new_call_argument.elisa" >/dev/null 2>&1
    region_new_call_compiler_status=$?
    if [[ "$region_new_call_compiler_status" -ne 0 ]]; then
        printf 'proof test matrix failed: stage1 rejected new[r] passed to a reference formal\n' >&2
        exit 1
    fi
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/region-statement.o" "$ROOT_DIR/examples/region_statement.elisa" >/dev/null 2>&1
region_statement_compiler_status=$?
if [[ "$region_statement_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected canonical region statement form\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-duplicate-alias.o" "$ROOT_DIR/examples/rejected_region_duplicate_mutable_alias.elisa" >/dev/null 2>&1
rejected_region_duplicate_alias_compiler_status=$?
if [[ "$rejected_region_duplicate_alias_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid duplicate-alias proof fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-assign-duplicate-owner.o" "$ROOT_DIR/examples/rejected_region_assign_duplicate_owner.elisa" >/dev/null 2>&1
rejected_region_assign_duplicate_owner_compiler_status=$?
if [[ "$rejected_region_assign_duplicate_owner_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid duplicate-owner assignment fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-bind-mutable-external.o" "$ROOT_DIR/examples/rejected_region_bind_mutable_external.elisa" >/dev/null 2>&1
rejected_region_bind_mutable_external_compiler_status=$?
if [[ "$rejected_region_bind_mutable_external_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid mutable region-bind fixture\n' >&2
    exit 1
fi
if [[ "$(basename "$SELF_HOST_COMPILER")" == "elisac-stage1" ]]; then
    "$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-call-result-duplicate-owner.o" "$ROOT_DIR/examples/rejected_region_call_result_duplicate_owner.elisa" >/dev/null 2>&1
    rejected_region_call_result_duplicate_owner_compiler_status=$?
    if [[ "$rejected_region_call_result_duplicate_owner_compiler_status" -ne 0 ]]; then
        printf 'proof test matrix failed: stage1 rejected the runtime-valid duplicate-owner call-result fixture\n' >&2
        exit 1
    fi
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-borrow-after-move.o" "$ROOT_DIR/examples/rejected_borrow_after_move.elisa" >/dev/null 2>&1
rejected_borrow_after_move_compiler_status=$?
if [[ "$rejected_borrow_after_move_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid borrow-after-move fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-negative-affine-difference.o" "$ROOT_DIR/examples/rejected_negative_affine_difference.elisa" >/dev/null 2>&1
rejected_negative_affine_difference_compiler_status=$?
if [[ "$rejected_negative_affine_difference_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the signed-affine regression fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-negative-affine-goal.o" "$ROOT_DIR/examples/rejected_negative_affine_goal.elisa" >/dev/null 2>&1
rejected_negative_affine_goal_compiler_status=$?
if [[ "$rejected_negative_affine_goal_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the signed-affine goal regression fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-borrow-call-duplicate-alias.o" "$ROOT_DIR/examples/rejected_borrow_call_duplicate_alias.elisa" >/dev/null 2>&1
rejected_borrow_call_duplicate_alias_compiler_status=$?
if [[ "$rejected_borrow_call_duplicate_alias_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid duplicate mutable call-alias fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/rejected-unsigned-overflow-goal.o" "$ROOT_DIR/examples/rejected_unsigned_overflow_goal.elisa" >/dev/null 2>&1
rejected_unsigned_overflow_goal_compiler_status=$?
if [[ "$rejected_unsigned_overflow_goal_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid unsigned overflow fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/nested-region-destroy.o" "$ROOT_DIR/examples/rejected_region_destroy_nested_without_binding.elisa" >/dev/null 2>&1
nested_region_destroy_compiler_status=$?
if [[ "$nested_region_destroy_compiler_status" -eq 0 ]]; then
    printf 'proof test matrix failed: compiler accepted nested destruction/reopening of an inherited region\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/kernel_replay_standalone.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] != "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] >= 895; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; declarations = {declaration["name"] for declaration in report["declaration_details"] if declaration["kind"] == "function" and declaration["verified"]}; required = {"proof_kernel_replay_node_at", "proof_kernel_replay_bool_at", "proof_kernel_replay_bool_set", "proof_kernel_replay_child_at", "proof_kernel_replay_child_range_valid", "proof_kernel_replay_scalar_kind", "proof_kernel_replay_arena_shape_valid", "proof_kernel_replay_arena_child_kind_valid", "proof_kernel_replay_model_value_at", "proof_kernel_replay_difference_query"}; assert required <= declarations; assert not any(f["kind"] == "contract-expression-unsupported" and "unsigned local" in f["message"] for f in report["findings"]); assert report["trust"]["trusted_assumptions"] == []'
kernel_replay_standalone_probe_status=${PIPESTATUS[1]}
if [[ "$kernel_replay_standalone_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: standalone replay audit has certificate gaps\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["source"]["bytes"] > 0; assert report["source"]["fingerprint"]["algorithm"] == "fnv1a32"; assert 0 <= report["source"]["fingerprint"]["value"] < 2**32; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert len(report["certificates"]) == report["replay"]["certificates"]; assert report["repair_queue"] == []; assert report["trust"]["trusted_assumptions"] == []; assert report["trust"]["trusted_boundary_facts"] == len(report["trust"]["boundary_facts"]); assert all(set(fact) == {"kind", "owner", "line", "kernel_root"} for fact in report["trust"]["boundary_facts"]); assert report["replay"]["gaps"] == 0; assert report["kernel"]["format"] == "elisa-proof-kernel-v1"; assert report["kernel"]["independent_replay"] is True; assert len(report["kernel"]["nodes"]) > 0; assert report["action_protocol"]["format"] == "elisa-proof-tactics-v1"; assert report["action_protocol"]["admission"] == "kernel-backed"; assert report["action_protocol"]["operations"] == ["assumption", "exact", "decide", "intro", "apply", "simp", "have", "instantiate", "rewrite", "split", "left", "right", "cases"]; assert report["action_protocol"]["branch_script"]["nested"] is True; assert report["action_protocol"]["branch_script"]["max_branch_depth"] == 32'
json_probe_status=$?
if [[ "$json_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: JSON report is not a valid structured proof state\n' >&2
    exit 1
fi
for replay_fixture in replay_constant arithmetic_identity equality_alias congruence summary_swapped_arguments quantifier collection_quantifier quantifier_structural_terms expression_witness call_stable_facts shared_borrow_calls writable_lend_calls region_lend_calls region_call_summary condition_call_positions product_sign frame_lifetime difference_constraints disjunctive_facts modulo_division_bounds proof_step_derivation pattern_proof pattern_or pinned_pattern pattern_scalar_literals total_match value_match value_match_nested_pure_call bounded_model loop_range_facts for_invariant for_loop_control_invariant indexed_frame slice_bounds indexn_kernel indexn_call_summary pure_index_call index_call_summary slice_call_summary fixed_array_bounds fixed_array_slice_bounds checked_index_fallback getelse_recovery getelse_checked_index getelse_call getelse_loop_control getelse_raise catch_expression catch_nested_pure_arm_call loop_control_invariant continue_decreases continue_decreases_branch shorthand_member constructor_kernel dogfood_kernel region_allocation region_statement region_auto_close region_new_call_argument region_new_mutable_call_argument; do
    "$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/$replay_fixture.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0'
    replay_probe_status=$?
    if [[ "$replay_probe_status" -ne 0 ]]; then
        printf 'proof test matrix failed: replay coverage for %s\n' "$replay_fixture" >&2
        exit 1
    fi
done
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_allocation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-open" in kinds and "resource-region-alloc" in kinds and "resource-region-bind" in kinds and "resource-region-alloc-discard" in kinds and "resource-region-close" in kinds'
region_allocation_probe_status=${PIPESTATUS[1]}
if [[ "$region_allocation_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: new[r] allocation/binding/discard transitions were not replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_generic_allocation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-param" in kinds and "resource-region-return-alloc" in kinds and "resource-region-return" in kinds and "resource-call-region" in kinds and "resource-call-result" in kinds'
region_generic_probe_status=${PIPESTATUS[1]}
if [[ "$region_generic_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic new[r] call/result was not replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_new_call_argument.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-call-alloc" in kinds and any(node["kind"] == "resource-call-arg" and node["operator"] == "region-new" for node in report["kernel"]["nodes"])'
region_new_call_probe_status=${PIPESTATUS[1]}
if [[ "$region_new_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: direct new[r] call temporary was not independently replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_new_mutable_call_argument.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-region-call-alloc" for node in report["kernel"]["nodes"])'
region_new_mutable_call_probe_status=${PIPESTATUS[1]}
if [[ "$region_new_mutable_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: mutable new[r] call temporary was not independently replayed\n' >&2
    exit 1
fi
set +e
rejected_region_new_return_report="$standalone_probe_dir/rejected-region-new-return.json"
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_new_return_argument.elisa" >"$rejected_region_new_return_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_reference_return_alias.elisa" >"$rejected_reference_return_alias_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_statement.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert kinds.count("resource-region-open") == 1 and kinds.count("resource-region-close") == 1 and "resource-region-alloc" in kinds and "resource-region-bind" in kinds and "resource-region-alloc-discard" in kinds'
region_statement_probe_status=${PIPESTATUS[1]}
if [[ "$region_statement_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: canonical region statement transitions were not replayed\n' >&2
    exit 1
fi
set +e
rejected_region_duplicate_alias_report="$standalone_probe_dir/rejected-region-duplicate-alias.json"
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_duplicate_mutable_alias.elisa" >"$rejected_region_duplicate_alias_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_assign_duplicate_owner.elisa" >"$rejected_region_assign_duplicate_owner_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_bind_mutable_external.elisa" >"$rejected_region_bind_mutable_external_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_negative_affine_difference.elisa" >"$rejected_negative_affine_difference_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_negative_affine_goal.elisa" >"$rejected_negative_affine_goal_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_call_duplicate_alias.elisa" >"$rejected_borrow_call_duplicate_alias_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_unsigned_overflow_goal.elisa" >"$rejected_unsigned_overflow_goal_report"
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
rejected_region_call_result_duplicate_owner_report="$standalone_probe_dir/rejected-region-call-result-duplicate-owner.json"
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_call_result_duplicate_owner.elisa" >"$rejected_region_call_result_duplicate_owner_report"
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_auto_close.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert kinds.count("resource-region-open") == 1 and kinds.count("resource-region-close") == 1'
region_auto_close_probe_status=${PIPESTATUS[1]}
if [[ "$region_auto_close_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: implicit region close was not replayed\n' >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_use_after_destroy.elisa" >/tmp/elisa-proof-rejected-region-use.json
rejected_region_use_status=$?
set -e
if [[ "$rejected_region_use_status" -ne 1 ]]; then
    printf 'proof test matrix failed: use after destroy was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open("/tmp/elisa-proof-rejected-region-use.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-use-after-destroy" for f in report["findings"]) or report["summary"]["semantic_errors"] > 0; assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: rejected region use report was incomplete\n' >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_generic_unmapped.elisa" >/tmp/elisa-proof-rejected-region-generic.json
rejected_region_generic_status=$?
set -e
if [[ "$rejected_region_generic_status" -ne 1 ]]; then
    printf 'proof test matrix failed: unmapped region-polymorphic call was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open("/tmp/elisa-proof-rejected-region-generic.json")); assert report["status"] == "failed"; assert any(f["kind"] == "region-call-opaque" for f in report["findings"]); assert report["replay"]["gaps"] == 0'; then
    printf 'proof test matrix failed: unmapped region-polymorphic call report was incomplete\n' >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_destroy_nested_without_binding.elisa" >/tmp/elisa-proof-rejected-nested-region-destroy.json
rejected_nested_region_destroy_status=$?
set -e
if [[ "$rejected_nested_region_destroy_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nested inherited-region destruction was accepted\n' >&2
    exit 1
fi
if ! python3 -c 'import json; report=json.load(open("/tmp/elisa-proof-rejected-nested-region-destroy.json")); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; assert any(f["kind"] == "region-destroy-unsupported" for f in report["findings"]) or report["summary"]["semantic_errors"] > 0'; then
    printf 'proof test matrix failed: nested inherited-region destruction report was incomplete\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/pattern_scalar_literals.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "char" for node in report["kernel"]["nodes"])'
pattern_scalar_literals_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_scalar_literals_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: scalar literal pattern facts\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/pinned_pattern.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] and goal["rule"] == "goal" for goal in report["goals"])'
pinned_pattern_probe_status=${PIPESTATUS[1]}
if [[ "$pinned_pattern_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pinned-pattern equality fact\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/pattern_or.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] and goal["rule"] == "goal" for goal in report["goals"])'
pattern_or_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_or_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: closed OR-pattern branch fact\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/shorthand_member.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "shorthand" and node["name"] == "None" for node in report["kernel"]["nodes"])'
shorthand_member_probe_status=${PIPESTATUS[1]}
if [[ "$shorthand_member_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: const-enum shorthand was not encoded as a replayed kernel atom\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/constructor_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert "construct" in kinds; assert "record-update" in kinds; assert "field-init" in kinds'
constructor_kernel_probe_status=${PIPESTATUS[1]}
if [[ "$constructor_kernel_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: constructor/update terms were not encoded for independent replay\n' >&2
    exit 1
fi
# The report exits 1: every slice equality is refused.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/slice_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["obligations"] == 9; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert not any(goal["proven"] for goal in report["goals"] if goal["rule"] != "resource-safety"); kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert "slice" in kinds; assert "absent" in kinds'
slice_kernel_probe_status=${PIPESTATUS[1]}
set -e
if [[ "$slice_kernel_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: slice terms were not encoded for independent replay\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/indexn_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 8; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert sum(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]) >= 2; assert any(node["kind"] == "index-n" and node["children_count"] == 2 for node in report["kernel"]["nodes"])'
indexn_kernel_probe_status=${PIPESTATUS[1]}
if [[ "$indexn_kernel_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: bounded multi-index terms were not checked and replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/quantifier_structural_terms.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 6; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert {"quantifier", "array", "if"} <= kinds; assert "construct" not in kinds'
quantifier_structural_probe_status=${PIPESTATUS[1]}
if [[ "$quantifier_structural_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: structured quantifier substitution was not replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/checked_index_fallback.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert any(goal["rule"] == "checked-index" and goal["proven"] for goal in report["goals"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
checked_index_certificate_probe_status=${PIPESTATUS[1]}
if [[ "$checked_index_certificate_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: checked-index safety certificate was not replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/getelse_recovery.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 4; assert any(goal["rule"] == "checked-get" and goal["proven"] for goal in report["goals"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
getelse_recovery_probe_status=${PIPESTATUS[1]}
if [[ "$getelse_recovery_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: get-else control recovery was not independently checked\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/getelse_checked_index.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "checked-get" and goal["proven"] for goal in report["goals"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
getelse_checked_index_probe_status=${PIPESTATUS[1]}
if [[ "$getelse_checked_index_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: checked-get safety certificate was not replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/getelse_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "maybe_value" for goal in report["goals"] for dependency in goal["dependencies"]); assert report["replay"]["gaps"] == 0'
getelse_call_probe_status=${PIPESTATUS[1]}
if [[ "$getelse_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: get-else guarded call summary was not applied\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/catch_expression.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 7; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "catch_probe_value" for goal in report["goals"] for dependency in goal["dependencies"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
catch_expression_probe_status=${PIPESTATUS[1]}
if [[ "$catch_expression_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: expression catch success/error paths were not checked independently\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/continue_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
continue_decreases_probe_status=${PIPESTATUS[1]}
if [[ "$continue_decreases_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: straight-line continue decreases path was not checked\n' >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_getelse_recovery.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "getelse-recovery-nonterminating" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_getelse_recovery_probe_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_getelse_recovery_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: falling-through get-else recovery was not rejected\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/conditional_proof.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 6; assert report["summary"]["proven"] == 6; assert report["replay"]["gaps"] == 0'
conditional_probe_status=${PIPESTATUS[1]}
if [[ "$conditional_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: conditional postcondition case elimination\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_conditional_proof.elisa" >/tmp/elisa-proof-rejected-conditional.json
rejected_conditional_status=$?
if [[ "$rejected_conditional_status" -ne 1 ]]; then
    printf 'proof test matrix failed: false conditional postcondition was accepted\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/implicit_structural_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
implicit_structural_status=${PIPESTATUS[1]}
if [[ "$implicit_structural_status" -ne 0 ]]; then
    printf 'proof test matrix failed: implicit structural termination\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/inferred_product_structural_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
inferred_product_structural_status=${PIPESTATUS[1]}
if [[ "$inferred_product_structural_status" -ne 0 ]]; then
    printf 'proof test matrix failed: inferred product structural termination\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/bounded_recursive_depth.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0'
bounded_recursive_depth_status=${PIPESTATUS[1]}
if [[ "$bounded_recursive_depth_status" -ne 0 ]]; then
    printf 'proof test matrix failed: bounded numeric recursive ranking\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_implicit_structural_decreases.elisa" >/tmp/elisa-proof-rejected-implicit-structural.json
rejected_implicit_structural_status=$?
if [[ "$rejected_implicit_structural_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nondecreasing implicit recursion was accepted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_inferred_product_structural_decreases.elisa" >/tmp/elisa-proof-rejected-inferred-product-structural.json
rejected_inferred_product_structural_status=$?
if [[ "$rejected_inferred_product_structural_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nondecreasing inferred product recursion was accepted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_bounded_recursive_depth.elisa" >/tmp/elisa-proof-rejected-bounded-depth.json
rejected_bounded_recursive_depth_status=$?
if [[ "$rejected_bounded_recursive_depth_status" -ne 1 ]]; then
    printf 'proof test matrix failed: unbounded numeric recursion was accepted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/nested_pure_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0'
nested_pure_call_status=${PIPESTATUS[1]}
if [[ "$nested_pure_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested certified-pure call expression\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/cast_not_index.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 2; assert report["replay"]["gaps"] == 0'
cast_not_index_status=${PIPESTATUS[1]}
if [[ "$cast_not_index_status" -ne 0 ]]; then
    printf 'proof test matrix failed: cast syntax treated as runtime indexing\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/early_return_index_guard.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
early_return_index_guard_probe_status=${PIPESTATUS[1]}
if [[ "$early_return_index_guard_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: early-return guard facts\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/loop_range_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(origin["kind"] == "loop-range" for goal in report["goals"] for origin in goal["fact_origins"] if origin); assert report["replay"]["gaps"] == 0'
loop_range_probe_status=${PIPESTATUS[1]}
if [[ "$loop_range_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: loop-derived collection bounds\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/for_invariant.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert any(origin and origin["kind"] == "loop-invariant" for goal in report["goals"] for origin in goal["fact_origins"]); assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0'
for_invariant_probe_status=${PIPESTATUS[1]}
if [[ "$for_invariant_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: ordinary for-loop invariant was not preserved and replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_for_invariant.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "disproved"; assert any(finding["kind"] == "invariant-not-preserved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_for_invariant_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_for_invariant_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: broken ordinary for-loop invariant was accepted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_for_invariant_scope.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert any(finding["kind"] == "loop-invariant-scope" and finding["status"] == "unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_for_invariant_scope_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_for_invariant_scope_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: out-of-scope for-loop invariant was accepted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/indexed_frame.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "index-lower" for goal in report["goals"]); assert any(goal["rule"] == "index-upper" for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
index_bounds_probe_status=${PIPESTATUS[1]}
if [[ "$index_bounds_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: indexed access bounds\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_index_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); lower = next(goal for goal in report["goals"] if goal["rule"] == "index-lower"); upper = next(goal for goal in report["goals"] if goal["rule"] == "index-upper"); assert lower["proven"] is True; assert any(origin and origin["kind"] == "type-bound" for origin in lower["fact_origins"]); assert upper["proven"] is False; assert report["status"] == "failed"'
unsigned_bound_probe_status=${PIPESTATUS[1]}
if [[ "$unsigned_bound_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler-backed unsigned lower bound\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_indexn_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert sum(finding["kind"] == "index-upper-unproven" for finding in report["findings"]) >= 2; assert report["replay"]["gaps"] == 0'
indexn_rejected_probe_status=${PIPESTATUS[1]}
if [[ "$indexn_rejected_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: unchecked multi-index dimensions were accepted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_pattern_or_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "pattern-unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
pattern_or_binding_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_or_binding_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: OR-pattern payload binding was accepted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/pure_index_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; lower = next(goal for goal in report["goals"] if goal["rule"] == "index-lower"); assert lower["proven"] is True; assert any(origin and origin["kind"] == "type-bound" for origin in lower["fact_origins"]); assert report["replay"]["gaps"] == 0'
pure_index_call_probe_status=${PIPESTATUS[1]}
if [[ "$pure_index_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pure-call fact preservation\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/index_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]); assert any(origin and origin["dependency"] == "identity_index" for goal in report["goals"] for origin in goal["fact_origins"] if origin); assert report["replay"]["gaps"] == 0'
index_call_summary_probe_status=${PIPESTATUS[1]}
if [[ "$index_call_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exact pure index result summary\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/indexn_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert sum(goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"]) >= 2; assert report["replay"]["gaps"] == 0'
indexn_call_summary_probe_status=${PIPESTATUS[1]}
if [[ "$indexn_call_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exact pure multi-index result summaries\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/slice_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert {goal["rule"] for goal in report["goals"]} >= {"slice-lower", "slice-upper", "slice-order"}; assert report["replay"]["gaps"] == 0'
slice_call_summary_probe_status=${PIPESTATUS[1]}
if [[ "$slice_call_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exact pure slice endpoint summaries\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_index_pure_result.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(goal["rule"] == "index-upper" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
rejected_index_pure_result_probe_status=${PIPESTATUS[1]}
if [[ "$rejected_index_pure_result_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pure index result did not retain its bound obligation\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/type_bound_state_flow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); lower = next(goal for goal in report["goals"] if goal["rule"] == "index-lower"); upper = next(goal for goal in report["goals"] if goal["rule"] == "index-upper"); assert report["status"] == "failed"; assert lower["proven"] is True; assert any(origin and origin["kind"] == "type-bound" for origin in lower["fact_origins"]); assert upper["proven"] is False; assert report["replay"]["gaps"] == 0'
type_bound_state_flow_probe_status=${PIPESTATUS[1]}
if [[ "$type_bound_state_flow_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: type-bound state-flow preservation\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_while_body_visibility.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "loop-invariant-missing" for finding in report["findings"]); assert any(goal["rule"] == "index-upper" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
while_body_visibility_probe_status=${PIPESTATUS[1]}
if [[ "$while_body_visibility_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: while-body obligation visibility\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_unverified_function_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "function-summary-unverified" for finding in report["findings"]); assert any(goal["name"] == "trusts_bad_claim" and not goal["proven"] for goal in report["goals"]); functions = [declaration for declaration in report["declaration_details"] if declaration["kind"] == "function"]; assert all(not declaration["verified"] for declaration in functions); assert functions[0]["verification_reason"] == "body-unverified"; assert functions[1]["verification_reason"] == "dependency-unverified"; assert report["replay"]["gaps"] == 0'
unverified_summary_probe_status=${PIPESTATUS[1]}
if [[ "$unverified_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: unverified executable summaries were trusted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_recursive_lemma.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "lemma-summary-unverified" for finding in report["findings"]); assert any(declaration["kind"] == "lemma" and not declaration["verified"] for declaration in report["declaration_details"]); assert any(declaration["name"] == "use_recursive_lemma" and declaration["verification_reason"] == "dependency-unverified" for declaration in report["declaration_details"]); assert report["replay"]["gaps"] == 0'
unverified_lemma_summary_probe_status=${PIPESTATUS[1]}
if [[ "$unverified_lemma_summary_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: unverified lemma summaries were trusted\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/slice_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert {goal["rule"] for goal in report["goals"]} >= {"slice-lower", "slice-upper", "slice-order"}; assert report["replay"]["gaps"] == 0'
slice_bounds_probe_status=${PIPESTATUS[1]}
if [[ "$slice_bounds_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: slice endpoint bounds\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/fixed_array_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 6; assert all(goal["proven"] for goal in report["goals"] if goal["rule"] == "index-upper"); assert any(origin and origin["kind"] == "type-bound" for goal in report["goals"] for origin in goal["fact_origins"] if goal["rule"] == "index-upper"); assert report["replay"]["gaps"] == 0'
fixed_array_bounds_probe_status=${PIPESTATUS[1]}
if [[ "$fixed_array_bounds_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: fixed-array type bounds\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/dogfood_kernel_core.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["verification_state"] == "proved"; assert report["summary"]["proven"] == 20; assert report["findings"] == []; assert report["summary"]["declarations"] == 9; assert report["summary"]["obligations"] == 20; assert report["replay"]["gaps"] == 0; assert [goal["goal_id"] for goal in report["goals"]] == list(range(len(report["goals"]))); assert [certificate["certificate_id"] for certificate in report["certificates"]] == list(range(len(report["certificates"]))); assert all(goal["certificate_id"] is not None for goal in report["goals"]); assert all(goal["certificate_id"] < len(report["certificates"]) for goal in report["goals"])'
dogfood_core_contract_probe_status=${PIPESTATUS[1]}
if [[ "$dogfood_core_contract_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: direct calls to dogfood kernel contracts\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/src/proof/kernel_core.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["verification_state"] == "proved"; assert report["summary"]["proven"] == 7; assert report["findings"] == []; assert report["summary"]["obligations"] == 7; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["kernel"]["independent_replay"] is True'
kernel_core_self_probe_status=${PIPESTATUS[1]}
if [[ "$kernel_core_self_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: kernel core does not verify itself\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_kernel_arena_cycle.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] for goal in report["goals"]); assert any(not goal["proven"] for goal in report["goals"])'
arena_cycle_probe_status=${PIPESTATUS[1]}
if [[ "$arena_cycle_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: cyclic source-neutral arena was not rejected fail-closed\n' >&2
    exit 1
fi
kernel_core_repeat_a="$(mktemp)"
kernel_core_repeat_b="$(mktemp)"
trap 'rm -f "$kernel_core_repeat_a" "$kernel_core_repeat_b"' EXIT
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/src/proof/kernel_core.elisa" >"$kernel_core_repeat_a"
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/src/proof/kernel_core.elisa" >"$kernel_core_repeat_b"
if ! cmp -s "$kernel_core_repeat_a" "$kernel_core_repeat_b"; then
    printf 'proof test matrix failed: repeated kernel reports are not byte-identical\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/bitwise_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0'
bitwise_probe_status=${PIPESTATUS[1]}
if [[ "$bitwise_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: fixed-width bitwise kernel coverage\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/proof_step_derivation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert any(origin["kind"] == "proof-step" and origin["premises"] > 0 for certificate in report["certificates"] for origin in certificate["fact_origins"]); assert report["replay"]["gaps"] == 0'
proof_trace_probe_status=${PIPESTATUS[1]}
if [[ "$proof_trace_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: derived proof-step provenance\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/function_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "identity_nonnegative" for goal in report["goals"] for dependency in goal["dependencies"]); assert any(dependency["kind"] == "function-summary" and dependency["name"] == "identity_nonnegative" for certificate in report["certificates"] for dependency in certificate["dependencies"]); index = next(item for item in report["dependency_index"] if item["name"] == "identity_nonnegative"); assert index["goal_ids"]; assert [item["name"] for item in report["declaration_details"]] == ["identity_nonnegative", "caller_uses_summary"]; assert report["declaration_details"][0]["parameters"] == ["x"]; assert report["declaration_details"][1]["requires"] == 1 and report["declaration_details"][1]["ensures"] == 1; assert report["replay"]["gaps"] == 0'
dependency_probe_status=${PIPESTATUS[1]}
if [[ "$dependency_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: explicit theorem dependency metadata\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/pattern_proof.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; assert any(origin["kind"] == "branch-condition" for certificate in report["certificates"] for origin in certificate["fact_origins"]); assert any(fact.get("operator") in ("==", ">=") for certificate in report["certificates"] for fact in certificate["facts"])'
pattern_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: ADT/pattern branch facts\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/total_match.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0'
total_match_probe_status=${PIPESTATUS[1]}
if [[ "$total_match_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: total returning match\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_frame_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["status"] == "disproved" for finding in report["findings"])'
disproved_probe_status=${PIPESTATUS[1]}
if [[ "$disproved_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: disproved finding classification\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_counterexample.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); findings = [finding for finding in report["findings"] if finding["kind"] == "ensure-unproven"]; repair = report["repair_queue"]; semantic = report["semantic_diagnostics"]; assert report["verification_state"] == "disproved"; assert len(semantic) == report["summary"]["semantic_diagnostics"]; assert any(item["severity"] == 1 and item["kind_code"] > 0 and item["message"] for item in semantic); assert any(finding["status"] == "disproved" and finding["counterexample_found"] and finding["counterexample"] and finding["counterexample"][0]["operator"] == "==" and finding["counterexample"][0]["left"].get("name") == "x" and finding["counterexample"][0]["right"].get("value") == 0 and finding["goal_id"] == repair[0]["goal_id"] for finding in findings); assert repair and repair[0]["failure"]["status"] == "disproved" and repair[0]["failure"]["counterexample_found"] and repair[0]["failure"]["goal_id"] == repair[0]["goal_id"]'
counterexample_probe_status=${PIPESTATUS[1]}
if [[ "$counterexample_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: deterministic counterexample witness\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_dogfood_kernel_core.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert [goal["goal_id"] for goal in report["goals"]] == list(range(len(report["goals"]))); assert [certificate["certificate_id"] for certificate in report["certificates"]] == list(range(len(report["certificates"]))); assert any(goal["certificate_id"] is None and not goal["proven"] for goal in report["goals"]); assert any(finding["kind"] == "ensure-unproven" and finding["status"] == "unknown" for finding in report["findings"])'
rejected_dogfood_json_status=${PIPESTATUS[1]}
if [[ "$rejected_dogfood_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: dogfood false-contract diagnostics\n' >&2
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
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_nested_disjoint_fields.elisa" >/dev/null
borrow_nested_disjoint_fields_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_four_nested_fields.elisa" >/dev/null
borrow_four_nested_fields_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_four_nested_alias.elisa" >/dev/null
rejected_borrow_four_nested_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_move_disjoint_field.elisa" >/dev/null
borrow_move_disjoint_field_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_call_summary.elisa" >/dev/null
borrow_call_summary_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_indexed_places.elisa" >/dev/null
borrow_indexed_places_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_multi_indexed_places.elisa" >/dev/null
borrow_multi_indexed_places_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_dynamic_whole_root.elisa" >/dev/null
borrow_dynamic_whole_root_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_dynamic_multi_whole_root.elisa" >/dev/null
borrow_dynamic_multi_whole_root_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_symbolic_disjoint.elisa" >/dev/null
borrow_symbolic_disjoint_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/rejected_borrow_symbolic_alias.elisa" >/dev/null
rejected_borrow_symbolic_alias_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_nested_expression.elisa" >/dev/null
borrow_nested_expression_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/borrow_reference_return_summary.elisa" >/dev/null
borrow_reference_return_summary_status=$?
"$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/value_match_pure_call.elisa" >/dev/null
value_match_pure_call_status=$?
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/captured_structural_accumulator.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert all(goal["proven"] for goal in report["goals"] if goal["rule"] == "structural-safety"); assert report["replay"]["gaps"] == 0'
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_continue_decreases_nonprogress.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "loop-decreases-unproven" for finding in report["findings"])'
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_shared_read.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(certificate["rule"] == "resource-safety" and certificate["replayed"] for certificate in report["certificates"]); assert any(node["kind"] == "resource-safety" for node in report["kernel"]["nodes"])'
borrow_shared_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_mutable_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(certificate["rule"] == "resource-safety" and certificate["replayed"] for certificate in report["certificates"]); assert any(node["kind"] == "resource-safety" for node in report["kernel"]["nodes"])'
borrow_mutable_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_lexical_scope.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(certificate["rule"] == "resource-safety" and certificate["replayed"] for certificate in report["certificates"]); assert any(node["kind"] == "resource-safety" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-scope" for node in report["kernel"]["nodes"])'
borrow_lexical_scope_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_disjoint_fields.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "field" and node["name"] == "left" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "field" and node["name"] == "right" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-write" and node["left"] != 0 for node in report["kernel"]["nodes"])'
borrow_disjoint_fields_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_nested_disjoint_fields.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert sum(1 for node in report["kernel"]["nodes"] if node["kind"] == "field" and node["name"] == "value") >= 1; assert sum(1 for node in report["kernel"]["nodes"] if node["kind"] == "field" and node["name"] == "sibling") >= 1'
borrow_nested_disjoint_fields_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_four_nested_fields.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "field" and node["name"] == "value" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "field" and node["name"] == "sibling" for node in report["kernel"]["nodes"])'
borrow_four_nested_fields_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_move_disjoint_field.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-move" and node["left"] != 0 for node in report["kernel"]["nodes"])'
borrow_move_disjoint_field_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "read_ref" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call-arg" and node["operator"] == "reference" for node in report["kernel"]["nodes"])'
borrow_call_summary_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_indexed_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "index" and node["value"] in (0, 1) for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call" and node["name"] == "read_index_ref" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call-arg" and node["operator"] == "borrow" for node in report["kernel"]["nodes"])'
borrow_indexed_places_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_multi_indexed_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert sum(node["kind"] == "index" for node in report["kernel"]["nodes"]) >= 4'
borrow_multi_indexed_places_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_dynamic_whole_root.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-bind" and node["operator"] == "shared" for node in report["kernel"]["nodes"])'
borrow_dynamic_whole_root_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_dynamic_multi_whole_root.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-bind" and node["operator"] == "shared" for node in report["kernel"]["nodes"])'
borrow_dynamic_multi_whole_root_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_symbolic_disjoint.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-disjoint" and node["operator"] == "!=" for node in report["kernel"]["nodes"])'
borrow_symbolic_disjoint_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_nested_expression.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "borrow_nested_catch_reader" for node in report["kernel"]["nodes"])'
borrow_nested_expression_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/borrow_reference_return_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "return_reference" for node in report["kernel"]["nodes"])'
borrow_reference_return_summary_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/value_match_pure_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "value_match_pure_call_leaf" for goal in report["goals"] for dependency in goal["dependencies"])'
value_match_pure_call_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/value_match_named_payload.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "value_match_named_payload_leaf" for goal in report["goals"] for dependency in goal["dependencies"])'
value_match_named_payload_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/catch_pure_arm_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(dependency["kind"] == "function-summary" and dependency["name"] == "catch_pure_arm_value" for goal in report["goals"] for dependency in goal["dependencies"])'
catch_pure_arm_call_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_value_match_payload_shadow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "ensure-unproven" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_value_match_payload_shadow_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_value_match_positional_payload.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_value_match_positional_payload_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_catch_impure_arm_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_catch_impure_arm_call_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/nested_frame.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call" and node["name"] == "set_inner_value" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call" and node["name"] == "set_inner_ref" for node in report["kernel"]["nodes"]); assert any(node["kind"] == "resource-call-arg" and node["operator"] == "borrow" and node["name"] == "inner" for node in report["kernel"]["nodes"])'
nested_frame_resource_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/resource_branch_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-join-move" and node["name"] == "x" for node in report["kernel"]["nodes"])'
resource_branch_join_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_write_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_field_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_field_write_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_field_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_field_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_nested_prefix.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_nested_prefix_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_four_nested_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-write-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_four_nested_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_move_parent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-move-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_move_parent_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_resource_use_after_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "resource-use-after-move" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_resource_use_after_move_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-move-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_move_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_escape.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-escape" and finding["status"] == "unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_escape_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert not any(finding["kind"] == "borrow-call-opaque" for finding in report["findings"]); findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("index-upper-unproven", "opaque_dynamic_borrow") in findings; assert ("index-upper-unproven", "opaque_dynamic_write") in findings; assert ("function-summary-unverified", "rejected_borrow_call") in findings; assert ("function-summary-unverified", "rejected_writable_borrow_call") in findings; assert report["replay"]["gaps"] == 0'
rejected_borrow_call_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_index_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_index_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_multi_index_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_multi_index_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_dynamic_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_dynamic_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_dynamic_multi_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_dynamic_multi_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_symbolic_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-alias-conflict" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0; assert not any(node["kind"] == "resource-disjoint" for node in report["kernel"]["nodes"])'
rejected_borrow_symbolic_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_call_alias.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-call-summary-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert not any(node["kind"] == "resource-call" and node["name"] == "set_inner_ref" for node in report["kernel"]["nodes"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_call_alias_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_resource_branch_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "resource-use-after-move" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_resource_branch_move_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_mutable_source.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-mutable-source" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_mutable_source_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_nested_catch.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-escape" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(node["kind"] == "resource-call" and node["name"] == "borrow_catch_source" for node in report["kernel"]["nodes"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_nested_catch_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_nested_match.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-escape" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(node["kind"] == "resource-call" and node["name"] == "borrow_match_reader" for node in report["kernel"]["nodes"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_nested_match_probe_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_value_match_impure_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "expression-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
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

if [[ "$rejected_nested_call_symbolic_value_status" -ne 1 || "$rejected_for_shadow_status" -ne 1 || "$rejected_match_shadow_status" -ne 1 || "$rejected_value_match_status" -ne 1 || "$rejected_loop_invariant_scope_status" -ne 1 || "$rejected_contract_call_status" -ne 1 || "$rejected_mutable_pure_contract_status" -ne 1 || "$rejected_pure_default_contract_status" -ne 1 || "$rejected_resource_expression_status" -ne 1 || "$rejected_unknown_call_result_status" -ne 1 || "$rejected_unknown_assert_reuse_status" -ne 1 || "$rejected_assert_nested_call_status" -ne 1 || "$rejected_mutual_recursive_pure_impure_member_status" -ne 1 || "$rejected_mutable_global_pure_contract_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_nested_call_symbolic_value=%s rejected_for_shadow=%s rejected_match_shadow=%s rejected_value_match=%s rejected_loop_invariant_scope=%s rejected_contract_call=%s rejected_mutable_pure_contract=%s rejected_pure_default_contract=%s rejected_resource_expression=%s rejected_parallel_proof_state=%s rejected_unknown_call_result=%s rejected_unknown_assert_reuse=%s rejected_assert_nested_call=%s rejected_mutual_recursive_pure_impure_member=%s rejected_mutable_global_pure_contract=%s\n' "$rejected_nested_call_symbolic_value_status" "$rejected_for_shadow_status" "$rejected_match_shadow_status" "$rejected_value_match_status" "$rejected_loop_invariant_scope_status" "$rejected_contract_call_status" "$rejected_mutable_pure_contract_status" "$rejected_pure_default_contract_status" "$rejected_resource_expression_status" "$rejected_parallel_proof_state_status" "$rejected_unknown_call_result_status" "$rejected_unknown_assert_reuse_status" "$rejected_assert_nested_call_status" "$rejected_mutual_recursive_pure_impure_member_status" "$rejected_mutable_global_pure_contract_status" >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_parallel_proof_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "parallel-state-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(goal["rule"] == "goal" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_parallel_nested_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "parallel-state-unsupported" and finding["status"] == "unsupported" for finding in report["findings"]); assert any(goal["rule"] == "goal" and not goal["proven"] for goal in report["goals"]); assert report["replay"]["gaps"] == 0'
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_checked_index_nested.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); repairs = report["repair_queue"]; assert [(item["rule"], item["failure"]["kind"]) for item in repairs] == [("index-lower", "index-lower-unproven"), ("index-upper", "index-upper-unproven")]; assert all(item["goal_id"] == item["failure"]["goal_id"] for item in repairs)'
checked_index_diagnostics_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_call_multiple_preconditions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); repairs = [item for item in report["repair_queue"] if item["failure"]["kind"] == "call-requires-unproven"]; assert len(repairs) == 2; assert all(item["goal_id"] == item["failure"]["goal_id"] for item in repairs); assert repairs[0]["goal_id"] != repairs[1]["goal_id"]; assert report["replay"]["gaps"] == 0'
multiple_preconditions_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/lexicographic_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["repair_queue"] == []; assert report["replay"]["gaps"] == 0'
lexicographic_repair_queue_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_void_postcondition.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); repairs = report["repair_queue"]; assert len(repairs) == 1; assert repairs[0]["failure"]["kind"] == "ensure-unproven"; assert repairs[0]["goal_id"] == repairs[0]["failure"]["goal_id"]'
void_postcondition_goal_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --goal 3 "$ROOT_DIR/examples/rejected_checked_index_nested.elisa" | python3 -c 'import json, sys; goal = json.load(sys.stdin); assert goal["format"] == "elisa-proof-goal-v1"; assert goal["status"] == "unknown"; assert goal["goal_id"] == 3; assert goal["goal"]["rule"] == "index-upper"; assert goal["goal"]["proposition"]["operator"] == "<"; assert goal["failure"]["goal_id"] == 3; assert goal["source"]["complete"] is False; assert "kernel" not in goal'
focused_open_goal_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --goal 7 "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; goal = json.load(sys.stdin); assert goal["status"] == "proved"; assert goal["goal"]["replay_status"] == "replayed"; assert goal["failure"] is None; assert goal["source"]["complete"] is True'
focused_proved_goal_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --goal 999999 "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; goal = json.load(sys.stdin); assert goal["status"] == "not_found"; assert goal["goal"] is None; assert goal["failure"] is None'
focused_missing_goal_status=${PIPESTATUS[0]}
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
theorem_catalog_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/lemma.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); traces = [trace for trace in report["kernel"]["fact_traces"] if trace["kind"] == "lemma-summary"]; assert report["status"] == "proved" and report["replay"]["gaps"] == 0; assert [trace["dependency"] for trace in traces] == ["nonnegative", "named_nonnegative"]; assert [len(trace["summary_bindings"]) for trace in traces] == [1, 2]; assert [len(trace["summary_require_goal_ids"]) for trace in traces] == [1, 2]; assert all(trace["summary_ensure_index"] == 0 for trace in traces); goals = report["goals"]; assert all(all(goals[goal_id]["proven"] and goals[goal_id]["replay_status"] == "replayed" for goal_id in trace["summary_require_goal_ids"]) for trace in traces)'
lemma_summary_provenance_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/rejected_lemma.elisa" | python3 -c 'import json, sys; catalog = json.load(sys.stdin); assert catalog["source"]["complete"] is False; assert len(catalog["theorems"]) == 1; theorem = catalog["theorems"][0]; assert theorem["name"] == "unsound"; assert theorem["verified"] is False; assert theorem["verification_reason"] == "body-unverified"; assert theorem["signature_valid"] is True; assert theorem["proof_goals_valid"] is True; assert theorem["proof_replay_complete"] is False; assert any(not goal["proven"] and goal["certificate_id"] is None and not goal["replayed"] for goal in theorem["proof_goals"])'
rejected_theorem_catalog_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/lemma_default_catalog.elisa" | python3 -c 'import json, sys; theorem = json.load(sys.stdin)["theorems"][0]; assert theorem["verified"] is True; assert theorem["parameters"] == ["x", "amount"]; assert theorem["parameter_defaults"] == [None, {"kind": "int", "value": 7}]'
default_theorem_catalog_status=${PIPESTATUS[0]}
python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/theorem_fingerprint_a.elisa" "$ROOT_DIR/examples/theorem_fingerprint_b.elisa" "$ROOT_DIR/examples/theorem_fingerprint_changed.elisa" <<'PY'
import json, subprocess, sys
def fingerprint(path):
    catalog = json.loads(subprocess.check_output([sys.argv[1], "--theorems", path]))
    theorem = next(item for item in catalog["theorems"] if item["name"] == "stable_identity")
    assert theorem["theorem_fingerprint"]["algorithm"] == "fnv1a32-kernel-theorem-v1"
    return theorem["theorem_fingerprint"]["value"]
original = fingerprint(sys.argv[2])
shifted = fingerprint(sys.argv[3])
changed = fingerprint(sys.argv[4])
assert original == shifted
assert original != changed
PY
stable_theorem_fingerprint_status=$?
"$ROOT_DIR/build/elisa-proof" --suggest 4 "$ROOT_DIR/examples/theorem_suggestions.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["format"] == "elisa-proof-suggestions-v1"; assert result["status"] == "ok"; assert result["source"]["admissible"] is True; assert result["goal_id"] == 4; assert result["goal_fingerprint"]["algorithm"] == "fnv1a32-kernel-goal-v1"; assert isinstance(result["goal_fingerprint"]["value"], int); assert len(result["candidates"]) == 1; candidate = result["candidates"][0]; assert candidate["theorem"] == "double_three"; assert candidate["ensure_index"] == 0; assert candidate["bindings"][0]["parameter"] == "value"; assert candidate["bindings"][0]["value"]["operator"] == "+"; assert candidate["premises"][0]["satisfied"] is True; assert candidate["premises_satisfied"] is True; assert candidate["applicable"] is True'
theorem_suggestion_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --suggest 1 "$ROOT_DIR/examples/rejected_lemma.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["source"]["admissible"] is False; assert result["candidates"] == []'
unverified_theorem_suggestion_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --suggest 8 "$ROOT_DIR/examples/theorem_suggestion_defaults.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["source"]["complete"] is True; assert [candidate["theorem"] for candidate in result["candidates"]] == ["safe_default"]; candidate = result["candidates"][0]; assert candidate["bindings"][1] == {"parameter": "amount", "value": {"kind": "int", "value": 7}}; assert candidate["applicable"] is True'
theorem_suggestion_default_status=${PIPESTATUS[0]}
"$ROOT_DIR/build/elisa-proof" --suggest 4 "$ROOT_DIR/examples/theorem_suggestion_structured.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["source"]["admissible"] is False; assert len(result["candidates"]) == 1; candidate = result["candidates"][0]; assert candidate["theorem"] == "tuple_fact"; assert candidate["bindings"][0]["value"]["operator"] == "+"; assert candidate["premises"][0]["satisfied"] is True; assert candidate["premises_satisfied"] is True; assert candidate["applicable"] is False'
theorem_suggestion_structured_status=${PIPESTATUS[0]}
python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/theorem_suggestions.elisa" <<'PY'
import subprocess, sys
first = subprocess.check_output([sys.argv[1], "--suggest", "4", sys.argv[2]])
second = subprocess.check_output([sys.argv[1], "--suggest", "4", sys.argv[2]])
assert first == second
PY
deterministic_theorem_suggestion_status=$?
"$ROOT_DIR/build/elisa-proof" --suggest 999999 "$ROOT_DIR/examples/theorem_suggestions.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["status"] == "not_found"; assert result["goal_fingerprint"] is None; assert result["candidates"] == []'
missing_theorem_suggestion_statuses=("${PIPESTATUS[@]}")
missing_theorem_suggestion_status=${missing_theorem_suggestion_statuses[0]}
missing_theorem_suggestion_json_status=${missing_theorem_suggestion_statuses[1]}
set -e
if [[ "$checked_index_diagnostics_status" -ne 1 || "$multiple_preconditions_status" -ne 1 || "$lexicographic_repair_queue_status" -ne 0 || "$void_postcondition_goal_status" -ne 1 || "$focused_open_goal_status" -ne 0 || "$focused_proved_goal_status" -ne 0 || "$focused_missing_goal_status" -ne 2 || "$focused_overflow_goal_status" -ne 2 || "$focused_negative_goal_status" -ne 2 || "$stable_goal_fingerprint_status" -ne 0 || "$theorem_catalog_status" -ne 0 || "$lemma_summary_provenance_status" -ne 0 || "$rejected_theorem_catalog_status" -ne 0 || "$default_theorem_catalog_status" -ne 0 || "$stable_theorem_fingerprint_status" -ne 0 || "$theorem_suggestion_status" -ne 0 || "$unverified_theorem_suggestion_status" -ne 0 || "$theorem_suggestion_default_status" -ne 0 || "$theorem_suggestion_structured_status" -ne 0 || "$deterministic_theorem_suggestion_status" -ne 0 || "$missing_theorem_suggestion_status" -ne 2 || "$missing_theorem_suggestion_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: repair diagnostics were not bound to exact goals\n' >&2
    exit 1
fi

if [[ "$rejected_index_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_index_bounds=%s\n' "$rejected_index_bounds_status" >&2
    exit 1
fi

if [[ "$rejected_index_call_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_index_call=%s\n' "$rejected_index_call_status" >&2
    exit 1
fi

if [[ "$rejected_index_pure_result_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_index_pure_result=%s\n' "$rejected_index_pure_result_status" >&2
    exit 1
fi

if [[ "$rejected_fixed_array_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_fixed_array_bounds=%s\n' "$rejected_fixed_array_bounds_status" >&2
    exit 1
fi

if [[ "$rejected_fixed_array_slice_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_fixed_array_slice_bounds=%s\n' "$rejected_fixed_array_slice_bounds_status" >&2
    exit 1
fi

if [[ "$captured_structural_accumulator_status" -ne 0 ]]; then
    printf 'proof test matrix failed: captured_structural_accumulator=%s\n' "$captured_structural_accumulator_status" >&2
    exit 1
fi

if [[ "$rejected_slice_bounds_status" -ne 1 || "$rejected_field_alias_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_slice_bounds=%s rejected_field_alias=%s\n' "$rejected_slice_bounds_status" "$rejected_field_alias_status" >&2
    exit 1
fi

if [[ "$nested_frame_status" -ne 0 || "$indexed_frame_status" -ne 0 || "$rejected_nested_frame_status" -ne 1 || "$rejected_deep_frame_status" -ne 1 || "$rejected_indexed_frame_status" -ne 1 || "$counterexample_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nested_frame=%s indexed_frame=%s rejected_nested_frame=%s rejected_deep_frame=%s rejected_indexed_frame=%s counterexample=%s\n' "$nested_frame_status" "$indexed_frame_status" "$rejected_nested_frame_status" "$rejected_deep_frame_status" "$rejected_indexed_frame_status" "$counterexample_status"
    exit 1
fi

if [[ "$modulo_division_bounds_status" -ne 0 || "$rejected_modulo_division_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: modulo_division_bounds=%s rejected_modulo_division_bounds=%s\n' "$modulo_division_bounds_status" "$rejected_modulo_division_bounds_status" >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_duplicate_quantifier.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(goal["rule"] == "quantifier-forall" and not goal["proven"] and goal["replay_status"] == "not_certified" for goal in report["goals"]); assert not any(certificate["rule"] == "quantifier-forall" for certificate in report["certificates"])'
duplicate_quantifier_status=${PIPESTATUS[0]}
set -e
if [[ "$duplicate_quantifier_status" -ne 1 ]]; then
    printf 'proof test matrix failed: duplicate dictionary quantifier binder was accepted\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["format"] == "elisa-proof-tactic-result-v1"; assert report["status"] == "proved"; assert report["source"]["fingerprint_match"] is True; assert report["tactic"]["certificate_replayed"] is True; assert report["tactic"]["kernel_trace_replayed"] is True; assert len(report["state"]["trace"]) == 2'
portable_script_status=${PIPESTATUS[0]}
if [[ "$portable_script_status" -ne 0 ]]; then
    printf 'proof test matrix failed: portable tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_branch.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["branch_certificate_replayed"] is True; assert report["branches"]["left"]["solved"] and report["branches"]["right"]["solved"]'
portable_branch_status=${PIPESTATUS[0]}
if [[ "$portable_branch_status" -ne 0 ]]; then
    printf 'proof test matrix failed: portable branch tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_branch.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["branch_certificate_replayed"] is True; assert report["branches"]["left"]["branches"]["left"]["solved"] is True; assert report["branches"]["left"]["branches"]["right"]["solved"] is True'
portable_nested_branch_status=${PIPESTATUS[0]}
if [[ "$portable_nested_branch_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested portable branch tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_cases.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["branch_certificate_replayed"] is True; assert report["branches"]["left"]["trace"][-1]["action"] == "cases"; assert report["branches"]["left"]["branches"]["left"]["facts"] == [{"kind": "bool", "value": True}]'
portable_nested_cases_status=${PIPESTATUS[0]}
if [[ "$portable_nested_cases_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested portable cases tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target_nested_branch.json" "$ROOT_DIR/examples/verified_branch.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert binding["bound"] and binding["goal_id"] == 1 and binding["previously_proven"]; assert binding["fingerprint_match"] is True; assert report["tactic"]["certificate_replayed"] is True; assert report["branches"]["left"]["branches"]["right"]["solved"] is True'
source_nested_branch_status=${PIPESTATUS[0]}
if [[ "$source_nested_branch_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound nested branch tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert binding["bound"] and binding["goal_id"] == 7 and binding["previously_proven"]; assert binding["fingerprint_match"] is True; assert report["tactic"]["status"] == "proved"; assert len(report["state"]["initial_facts"]) == 2; assert any(fact["kind"] == "call" and fact["callee"]["name"] == "__elisa_primitive_scalar_type" for fact in report["state"]["initial_facts"])'
source_bound_script_status=${PIPESTATUS[0]}
if [[ "$source_bound_script_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound tactic script\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert report["admission_scope"] == "target"; assert report["source"]["status"] == "failed"; assert report["source"]["complete"] is False; assert report["source"]["admissible"] is True; assert binding["bound"] and binding["goal_id"] == 1 and not binding["previously_proven"]; assert binding["goal_fingerprint"]["value"] == 3193966897 and binding["fingerprint_match"] is True; assert report["tactic"]["certificate_replayed"] is True; assert any(fact["kind"] == "call" and not fact.get("argument_names") for fact in report["state"]["initial_facts"])'
repair_target_status=${PIPESTATUS[0]}
if [[ "$repair_target_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound tactic could not repair an open target\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target_shifted.json" "$ROOT_DIR/examples/tactic_repair_target_shifted.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert binding["goal_id"] == 2; assert binding["goal_fingerprint"]["value"] == 3193966897; assert binding["fingerprint_match"] is True'
shifted_repair_target_status=${PIPESTATUS[0]}
if [[ "$shifted_repair_target_status" -ne 0 ]]; then
    printf 'proof test matrix failed: stable target proof did not survive unrelated source insertion\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target_stale_goal.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["source_goal_binding"]["fingerprint_match"] is False; assert report["tactic"]["valid"] is False; assert "goal_fingerprint" in report["tactic"]["reason"]'
stale_repair_target_status=${PIPESTATUS[0]}
set -e
if [[ "$stale_repair_target_status" -ne 1 ]]; then
    printf 'proof test matrix failed: stale target goal fingerprint was admitted\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target.json" "$ROOT_DIR/examples/rejected_tactic_repair_semantic.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["source"]["complete"] is False; assert report["source"]["admissible"] is False; assert report["tactic"]["certificate_replayed"] is True'
semantic_repair_status=${PIPESTATUS[0]}
set -e
if [[ "$semantic_repair_status" -ne 1 ]]; then
    printf 'proof test matrix failed: target tactic laundered a semantic source error\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_forged_resource_target.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["source_goal_binding"]["goal_id"] == 0; assert report["tactic"]["valid"] is False; assert report["tactic"]["certificate_replayed"] is False'
resource_target_status=${PIPESTATUS[0]}
set -e
if [[ "$resource_target_status" -ne 1 ]]; then
    printf 'proof test matrix failed: proposition tactic replaced a resource certificate\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_after_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "resource-use-after-move" and finding["message"] == "a borrow cannot be created from a moved resource binding" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_after_move_probe_status=${PIPESTATUS[0]}
set -e
if [[ "$rejected_borrow_after_move_probe_status" -ne 1 ]]; then
    printf 'proof test matrix failed: borrow-after-move was not rejected with replayable evidence\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/congruence.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; assert report["findings"] == []; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"congruence_sum", "congruence_difference", "congruence_product", "congruence_nested", "congruence_chain", "congruence_boolean", "congruence_bitwise", "congruence_conditional", "congruence_character", "congruence_boolean_parameters", "congruence_bounded_unsigned", "congruence_pure_call_result"} <= names'
congruence_status=${PIPESTATUS[1]}
if [[ "$congruence_status" -ne 0 ]]; then
    printf 'proof test matrix failed: ground congruence closure did not carry equalities through deterministic formers\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_congruence.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"disequality_premise", "order_premise", "disjunctive_premise", "unrelated_operand", "distinct_former", "struct_equality_premise", "indexed_element", "constructed_aggregate", "call_congruence", "cross_width", "wrapping_operand"}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}; assert not (refused & claimed); assert refused <= {finding["name"] for finding in report["findings"]}'
rejected_congruence_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_congruence_status" -ne 0 ]]; then
    printf 'proof test matrix failed: congruence admitted a goal outside the deterministic term fragment\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_reflexivity.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"reflexive_equality", "reflexive_order", "reflexive_reverse_order", "symmetric_equality", "local_reflexive_equality", "field_reflexive_equality", "field_reflexive_order", "element_reflexive_equality", "opaque_call_reflexive_equality", "struct_element_binder_reflexive_equality"}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}; assert not (refused & claimed); assert refused <= {finding["name"] for finding in report["findings"]}'
rejected_reflexivity_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_reflexivity_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a user-defined equality was assumed reflexive, symmetric, or coherent with ordering\n' >&2
    exit 1
fi

# Expression-level type witnesses: struct fields, container counts and elements to the declared
# depth, const-enum values, and verified total-pure call results are witnessed by exact term.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/expression_witness.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["obligations"] == 43; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"range_binder_reflexive", "element_binder_reflexive", "field_element_binder_reflexive", "element_binder_congruence", "asserted_opaque_binding", "field_reflexive", "nested_field_reflexive", "field_through_reference", "element_reflexive", "count_reflexive", "multi_index_reflexive", "nested_index_reflexive", "field_congruence", "element_congruence", "local_field_reflexive", "const_enum_reflexive", "pure_call_reflexive", "bound_opaque_call"} <= names; witnesses = [fact for certificate in report["certificates"] for fact in certificate["facts"] if fact["kind"] == "call" and fact["callee"]["name"] in ("__elisa_primitive_scalar_type", "__elisa_primitive_scalar_element")]; assert any(fact["arguments"][0]["kind"] == "field" for fact in witnesses); assert any(fact["callee"]["name"] == "__elisa_primitive_scalar_element" for fact in witnesses)'
expression_witness_status=${PIPESTATUS[1]}
set -e
if [[ "$expression_witness_status" -ne 0 ]]; then
    printf 'proof test matrix failed: expression-level type witnesses\n' >&2
    exit 1
fi

# Elisa admits no `==` between aggregates, and struct `==` is a user `__eq__`; every such goal
# must be refused without a certificate while its form still lowers into the arena.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_aggregate_equality.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"array_equality", "nested_array_equality", "tuple_equality", "dictionary_equality", "construct_equality", "update_equality", "quantified_array_equality", "quantified_tuple_equality", "quantified_dictionary_equality", "quantified_construct_equality"}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}; assert not claimed; assert refused <= {finding["name"] for finding in report["findings"]}; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert {"array", "tuple", "dict", "dict_entry", "construct", "record-update", "field-init", "quantifier"} <= kinds'
rejected_aggregate_equality_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_aggregate_equality_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an aggregate equality was admitted\n' >&2
    exit 1
fi

# A fact over a by-value scalar the body never lets escape survives an opaque call, and a
# conjunctive guard entails each of its parts. Both are needed to re-establish a bounded-recursion
# precondition at a second call; each conjunct is a derived fact the kernel re-proves.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/call_stable_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"survives_state_writing_call", "survives_second_call", "survives_branch_join", "survives_call_guard", "survives_returning_branch"} <= names; origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}; assert "branch-conjunct" in origins'
call_stable_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$call_stable_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: call-stable facts and branch conjuncts\n' >&2
    exit 1
fi

# The boundary of those two rules: a scalar the callee can write, a scalar a branch assigns, and a
# disjunction are all refused. Nothing here may be proven.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_call_stable_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"aliased_scalar", "assigned_in_branch", "disjunctive_branch", "negated_conjunctive_guard", "rebound_after_guard"}; assert refused <= {finding["name"] for finding in report["findings"]}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety" and goal["name"] in refused and "depth <= 127" in str(goal)}; assert not claimed'
rejected_call_stable_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_call_stable_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fact survived a call or a branch that could falsify it\n' >&2
    exit 1
fi

# A call that lends only shared references cannot change the caller's resource state, so it is
# admitted from the callee's declared modes with no body summary. That is the only path open to a
# recursive component, which can never consume one of its own summaries.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/shared_borrow_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; kinds = {node["kind"] for node in nodes}; assert "resource-call-lend" in kinds; shared = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert all(node["left"] == 0 and node["children_count"] == node["auxiliary"] * 2 for node in shared); formals = [nodes[child] for node in shared for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]; assert formals; assert all(formal["kind"] == "resource-call-formal" for formal in formals); assert all(formal["operator"] in ("value", "external-shared") for formal in formals); assert any(formal["operator"] == "external-shared" for formal in formals)'
shared_borrow_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$shared_borrow_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: shared-reference calls\n' >&2
    exit 1
fi

# A capability the callee may write through, one that outlives the call, and one the caller no
# longer holds all still require the callee's own converged summary.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_shared_borrow_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "recursive_reference_return") in findings; assert ("resource-use-after-move", "lends_moved_value") in findings; assert ("borrow-call-opaque", "lends_shared_while_mutably_borrowed") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_shared_borrow_calls_status=${PIPESTATUS[1]}
set -e
# An exclusive lend needs no callee summary either: the callee can do no more than write through
# the reference, so the caller over-approximates the call by a write to the whole lent place. Every
# exclusive capability must be one the caller holds alone.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/writable_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; lends = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert lends; formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]; assert any(formal["operator"] == "external-mutable" for formal in formals); assert any(formal["operator"] == "external-shared" for formal in formals)'
writable_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$writable_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: confined writable lending\n' >&2
    exit 1
fi

# Two exclusive capabilities over one place, a shared one beside an exclusive one, and an
# exclusive lend across a live borrow are each refused with no event recorded.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_writable_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "swap_pair") in findings; assert ("borrow-call-opaque", "read_and_write") in findings; assert ("borrow-call-opaque", "touch_borrowed") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_writable_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_writable_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unconfined exclusive lend was admitted\n' >&2
    exit 1
fi

# A lifetime parameter does not stop a call from being a lend: the callee may allocate into a
# mapped caller region and can never close one. Every formal lifetime must be pinned to a region
# active at the call, and every region-carrying actual must land on a formal declaring it.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; lends = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert lends; assert all(node["children_count"] == node["auxiliary"] * 2 + node["right"] for node in lends); assert any(node["right"] == 2 for node in lends); maps = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"] * 2:node["children_start"] + node["children_count"]]]; assert maps; assert all(entry["kind"] == "resource-call-region" and entry["operator"] == "param" and entry["name"] and entry["secondary_name"] for entry in maps); formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["auxiliary"] * 2]]; assert any(formal["secondary_name"] for formal in formals)'
region_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$region_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic lending\n' >&2
    exit 1
fi

# A region-polymorphic callee that does have a converged summary must compose into its caller. A
# construction's left edge is the constructed type, not a value; a record update's left edge is
# the base record and still is one.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert {"resource-region-alloc", "construct", "record-update", "resource-call"} <= kinds'
region_call_summary_status=${PIPESTATUS[1]}
set -e
if [[ "$region_call_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic callee summary composition\n' >&2
    exit 1
fi

# A branch condition may carry an executable call wherever that call runs whenever the condition
# is evaluated, not only at the root. A call that may be skipped stays refused.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"bare_call", "negated_call", "compared_call", "short_circuit_left", "arithmetic_call", "guarded_index"} <= names'
condition_call_positions_status=${PIPESTATUS[1]}
set -e
if [[ "$condition_call_positions_status" -ne 0 ]]; then
    printf 'proof test matrix failed: executable calls in branch conditions\n' >&2
    exit 1
fi

# The sign of a product is decidable from its operands' signs. The producer and the replay kernel
# state the rule identically, so every one of these must also replay: a tier only the producer had
# would show up as a gap, not a proof.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/product_sign.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"nonnegative_product", "negative_operands", "mixed_operands", "strict_product", "strict_negative", "mirrored_forms"} <= names'
product_sign_status=${PIPESTATUS[1]}
set -e
if [[ "$product_sign_status" -ne 0 ]]; then
    printf 'proof test matrix failed: product sign reasoning\n' >&2
    exit 1
fi

# A strict conclusion needs strict premises, a mixed pair is not nonnegative, one known sign is not
# two, a bound other than zero is not a sign, and sign facts about other terms say nothing here.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_product_sign.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert not any(goal["proven"] and goal["rule"] != "resource-safety" for goal in report["goals"]); refused = {finding["name"] for finding in report["findings"] if finding["kind"] == "ensure-unproven"}; assert {"strict_from_nonstrict", "mixed_claimed_nonnegative", "one_operand_known", "nonzero_bound", "signs_of_other_terms"} <= refused'
rejected_product_sign_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_product_sign_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unsound product sign was concluded\n' >&2
    exit 1
fi

# A lifetime parameter may be pinned to the caller's own frame: a caller local outlives any call
# that borrows it. The frame is not a region with an extent, so both sides check the same thing in
# its place — the actual is a place the caller holds outright.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/frame_lifetime.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; assert any(node["kind"] == "resource-call-region" and node["secondary_name"] == "@call-frame" for node in nodes)'
frame_lifetime_status=${PIPESTATUS[1]}
set -e
if [[ "$frame_lifetime_status" -ne 0 ]]; then
    printf 'proof test matrix failed: frame lifetime pinning\n' >&2
    exit 1
fi

# A moved binding is no longer a place the caller holds, and a lifetime no formal carries is pinned
# by nothing at all.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_frame_lifetime.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("resource-use-after-move", "lends_moved_local") in findings; assert ("region-call-opaque", "lends_moved_local") in findings; assert ("region-call-opaque", "unreceived_lifetime") in findings; assert not any(node["kind"] == "resource-call-region" and node["secondary_name"] == "@call-frame" for node in report["kernel"]["nodes"])'
rejected_frame_lifetime_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_frame_lifetime_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a lifetime was pinned to a frame that vouches for nothing\n' >&2
    exit 1
fi

# A region-owned actual reaching a formal that declares no lifetime is a capability the callee
# cannot name, so a *lend* may carry it; the callee's own trace is what places it on the summary
# path, where the refusal stands.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/unnamed_lifetime_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; resource = {goal["name"]: goal["proven"] for goal in report["goals"] if goal["rule"] == "resource-safety"}; assert resource.get("lends_region_value") is True; assert resource.get("lends_region_value_exclusively") is True; kinds = {finding["kind"] for finding in report["findings"]}; assert "region-call-opaque" not in kinds; assert "borrow-call-opaque" not in kinds'
unnamed_lifetime_status=${PIPESTATUS[1]}
set -e
if [[ "$unnamed_lifetime_status" -ne 0 ]]; then
    printf 'proof test matrix failed: lending a region-owned actual to an unnamed lifetime\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_unnamed_lifetime_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("region-call-opaque", "lends_region_value_to_summary") in findings'
rejected_unnamed_lifetime_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_unnamed_lifetime_status" -ne 0 ]]; then
    printf 'proof test matrix failed: the summary path admitted an unnamed lifetime\n' >&2
    exit 1
fi

# `for x in xs |a, b|:` reaches the statement walker as an expression statement holding a captured
# block. Refusing it invalidated the enclosing path, which skipped the loop body entirely; the
# write-back is modelled instead, so obligations inside and after the loop are both checked.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/captured_block.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("obligations_after_the_loop_are_checked", "index-upper") in proven; assert ("obligations_inside_the_loop_are_checked", "index-upper") in proven; assert not report["findings"]'
captured_block_status=${PIPESTATUS[1]}
set -e
if [[ "$captured_block_status" -ne 0 ]]; then
    printf 'proof test matrix failed: captured block statements\n' >&2
    exit 1
fi

# The write-back is havocked, so nothing established before the loop survives it, and an
# unprovable obligation inside the body stays visible instead of vanishing with the path.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_captured_block.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("fact_must_not_survive", "goal")] is False; assert goals[("value_must_not_survive", "goal")] is False; assert goals[("obligation_inside_is_not_skipped", "index-upper")] is False'
rejected_captured_block_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_captured_block_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a captured block let outer state survive\n' >&2
    exit 1
fi

# The capture list is the block's whole reach, so a binding it does not name keeps both its
# symbolic value and its facts across the block; a binding it does name keeps neither.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/uncaptured_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("value_outside_the_capture_list_survives", "goal") in proven; assert ("fact_outside_the_capture_list_survives", "goal") in proven; assert not report["findings"]'
uncaptured_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$uncaptured_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an uncaptured binding did not survive a captured block\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_uncaptured_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("overwritten_binding_must_not_survive", "goal")] is False; assert goals[("zero_iteration_fact_must_not_escape", "goal")] is False'
rejected_uncaptured_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_uncaptured_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a captured binding survived its own captured block\n' >&2
    exit 1
fi

# The capture list is not a bound on what a block writes: the compiler accepts a block whose body
# assigns an outer binding the list omits. Every such binding must lose its value and its facts.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_uncaptured_block_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; written = ("assigned_without_being_captured", "assigned_under_a_branch", "written_through_a_reference", "assigned_in_a_nested_block", "fact_over_a_written_binding"); assert all((owner, "call-requires-unproven") in owners for owner in written); goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert all(goals[(owner, "goal")] is False for owner in written); assert {kind for _, kind in owners} == {"call-requires-unproven"}'
rejected_uncaptured_block_write_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_uncaptured_block_write_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a binding written outside a block capture list kept its state\n' >&2
    exit 1
fi

# A call reaches the caller's state only through references and globals, so a by-value scalar
# nothing in the body references keeps its recorded value across the call; at a branch join, a
# value every reaching arm still agrees on keeps it too. A referenced binding, a value recorded in
# terms of one, and a value an arm overwrote must all still be forgotten.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/call_boundary_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert not [goal for goal in report["goals"] if not goal["proven"]]; proven = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] == "goal"}; assert {"loop_binder_survives_a_declaration_call", "value_survives_a_declaration_call", "value_survives_an_assignment_call", "value_survives_a_statement_call", "loop_binder_survives_a_guarded_call", "value_survives_a_returning_branch"} <= proven; assert not report["findings"]'
call_boundary_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$call_boundary_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a binding no callee can reach did not survive the call boundary\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_call_boundary_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {finding["name"] for finding in report["findings"] if finding["kind"] == "ensure-unproven"}; assert owners == {"referenced_value_must_not_survive", "value_over_a_referenced_binding_must_not_follow_it", "referenced_value_must_not_survive_a_statement_call", "value_overwritten_in_one_arm_must_not_survive", "value_overwritten_in_the_surviving_arm_must_not_survive"}; assert all(goal["proven"] for goal in report["goals"] if goal["rule"] != "goal")'
rejected_call_boundary_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_call_boundary_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a binding a callee or an arm can rewrite survived the boundary\n' >&2
    exit 1
fi

# An impure call on the right of `and`/`or` may not run. It is checked and havocked as if it ran,
# nothing only the run establishes survives, and the statement no longer invalidates its path.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/short_circuit_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["findings"] == []; assert all(goal["proven"] for goal in report["goals"]); verified = {declaration["name"] for declaration in report["declaration_details"] if declaration["kind"] == "function" and declaration["verified"]}; assert {"guard_with_a_skippable_call", "declaration_with_a_skippable_call", "return_with_a_skippable_call", "caller_of_the_returning_shape"} <= verified'
short_circuit_call_status=${PIPESTATUS[1]}
set -e
if [[ "$short_circuit_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a short-circuited impure call still invalidates its path\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_short_circuit_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; kinds = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert kinds == {("skipped_call_must_not_establish_and", "ensure-unproven"), ("skipped_call_must_not_establish_or", "ensure-unproven"), ("skipped_call_must_not_establish_a_guard", "ensure-unproven"), ("pre_call_value_must_not_survive", "ensure-unproven"), ("skipped_requires_is_still_checked", "call-requires-unproven")}; assert not any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); goals = {goal["name"]: goal["proven"] for goal in report["goals"] if goal["rule"] == "goal" and goal["name"] != "reset"}; assert goals and not any(goals.values())'
rejected_short_circuit_call_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_short_circuit_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a skipped call established something, or lost its precondition\n' >&2
    exit 1
fi

# A branch condition carrying an opaque placeholder never enters a certificate. Its admissible
# conjuncts are recorded as branch facts in their own right, so a goal that needs one both proves
# and replays; the conjunct carrying the placeholder is not recorded in any form.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/branch_conjunct_placeholder.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; goals = [goal for goal in report["goals"] if goal["name"] == "conjunct_beside_a_placeholder" and goal["rule"] == "goal"]; assert goals and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in goals); assert any(origin["kind"] == "branch-condition" for goal in goals for origin in goal["fact_origins"]); assert not any(origin["kind"] == "branch-conjunct" for goal in goals for origin in goal["fact_origins"])'
branch_conjunct_placeholder_status=${PIPESTATUS[1]}
set -e
if [[ "$branch_conjunct_placeholder_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a conjunct beside a placeholder did not prove and replay\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_branch_conjunct_placeholder.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {goal["line"]: goal for goal in report["goals"] if goal["name"] == "placeholder_conjunct_must_not_become_a_fact" and goal["rule"] == "goal"}; assert goals and any(not goal["proven"] for goal in goals.values()); assert not any(origin["kind"] == "branch-conjunct" for goal in goals.values() for origin in goal["fact_origins"]); assert ("placeholder_conjunct_must_not_become_a_fact", "ensure-unproven") in {(finding["name"], finding["kind"]) for finding in report["findings"]}'
rejected_branch_conjunct_placeholder_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_branch_conjunct_placeholder_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a placeholder conjunct became a fact, or a derivation from an inadmissible premise survived\n' >&2
    exit 1
fi

# A loop body is checked for an arbitrary iteration: every binding it may rewrite is opaque at
# entry, and only the loop condition, the established invariants and the untouched bindings are
# known inside. The entry value of a rewritten binding must not stand in for an iteration.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/loop_entry_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = [goal for goal in report["goals"] if goal["rule"] != "resource-safety"]; assert goals and all(goal["proven"] for goal in goals); names = {goal["name"] for goal in goals}; assert {"unwritten_binding_keeps_its_fact", "condition_bounds_the_body", "sound_invariant_is_preserved", "binder_range_survives"} <= names; assert sum(1 for goal in goals if goal["name"] == "sound_invariant_is_preserved") == 2; kinds = {finding["kind"] for finding in report["findings"]}; assert kinds == {"loop-invariant-missing"}'
loop_entry_state_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_entry_state_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop body lost a fact that holds on every iteration\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_loop_entry_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {}; [goals.setdefault(goal["name"], []).append(goal["proven"]) for goal in report["goals"] if goal["rule"] == "goal"]; assert goals["entry_value_must_not_reach_the_body"] == [False]; assert goals["entry_value_must_not_reach_an_uncaptured_body"] == [False]; assert False in goals["false_invariant_must_not_be_preserved"]; assert not all(goals["break_must_not_yield_the_exit_condition"]); owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert ("entry_value_must_not_reach_the_body", "call-requires-unproven") in owners; assert ("entry_value_must_not_reach_an_uncaptured_body", "call-requires-unproven") in owners; assert ("false_invariant_must_not_be_preserved", "invariant-not-preserved") in owners; assert ("break_must_not_yield_the_exit_condition", "ensure-unproven") in owners'
rejected_loop_entry_state_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_entry_state_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop body used the entry value of a binding it rewrites\n' >&2
    exit 1
fi

# An invariant-less loop still runs its body only when the condition holds, and a shared borrow's
# element count is stable across a call. Together these discharge the dominant loop shape here.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/loop_condition_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("while_condition_bounds_the_body", "index-upper") in proven; assert ("shared_extent_survives_a_call_in_the_body", "index-upper") in proven; assert ("shared_extent_survives_a_call", "index-upper") in proven; kinds = {finding["kind"] for finding in report["findings"]}; assert kinds == {"loop-invariant-missing"}'
loop_condition_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_condition_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop condition or a shared extent did not reach the body\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_loop_condition_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("unrelated_condition_proves_no_bound", "index-upper")] is False; assert goals[("mutable_extent_must_not_survive_a_call", "index-upper")] is False; assert goals[("entry_value_must_not_reach_the_body", "goal")] is False; assert any(f["kind"] == "call-requires-unproven" for f in report["findings"])'
rejected_loop_condition_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_condition_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop condition or a mutable extent claimed too much\n' >&2
    exit 1
fi

# A mutable global is the one path a shared borrow does not exclude, so the extent rule is
# withdrawn from any program that declares one.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_shared_extent_global.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("borrowed_extent_must_not_survive", "index-upper")] is False'
rejected_shared_extent_global_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_shared_extent_global_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a shared extent survived a mutable global write\n' >&2
    exit 1
fi

# Structural transitivity reaches goals the difference engine cannot name, and reaches nothing
# built out of a user comparison.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/comparison_chain.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["verification_state"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["findings"] == []; assert report["trust"]["trusted_assumptions"] == []'
comparison_chain_status=${PIPESTATUS[1]}
set -e
if [[ "$comparison_chain_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a comparison chain did not reach an unnameable bound\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_comparison_chain.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("struct_order_is_not_transitive", "goal")] is False; assert goals[("struct_non_strict_order_is_not_transitive", "goal")] is False; assert goals[("non_strict_chain_gives_no_strict_goal", "goal")] is False; assert goals[("wrong_direction_chain", "goal")] is False'
rejected_comparison_chain_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_comparison_chain_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a comparison chain claimed a user comparison or a direction it does not have\n' >&2
    exit 1
fi

# A callee whose only findings widen its own state still exports its summary, and says so.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/widened_state_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; kinds = {f["kind"] for f in report["findings"]}; assert kinds == {"loop-invariant-missing"}; assert not [g for g in report["goals"] if not g["proven"]]; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert ("caller_may_use_that_summary", "goal") in proven; assert ("caller_may_use_that_one_too", "goal") in proven; assert ("two_levels_above", "goal") in proven; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["loop_is_havocked_but_the_contract_holds"] == "verified"; assert reasons["caller_may_use_that_summary"] == "verified"; assert reasons["missing_invariant_is_havocked_too"] == "contract-verified-widened-state"; assert reasons["caller_may_use_that_one_too"] == "contract-verified-widened-state"; assert reasons["two_levels_above"] == "contract-verified-widened-state"; assert reasons["untouched_leaf"] == "verified"; assert reasons["untouched_caller"] == "verified"'
widened_state_summary_status=${PIPESTATUS[1]}
set -e
if [[ "$widened_state_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a widened-state contract did not export its summary, or did not say so\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_widened_state_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(f["name"], f["kind"]) for f in report["findings"]}; assert ("caller_gets_no_summary", "function-summary-unverified") in owners; assert ("caller_gets_no_summary_from_an_unproven_index", "function-summary-unverified") in owners; assert ("writes_outside_its_frame", "frame-write-outside") in owners; assert ("caller_gets_no_frame", "function-summary-unverified") in owners; assert ("breaks_what_it_preserves", "frame-preserve-write") in owners; assert ("caller_must_lose_the_fact", "ensure-unproven") in owners; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; usable = ("verified", "contract-verified-widened-state"); assert reasons["unproven_ensure_with_a_loop"] not in usable; assert reasons["unproven_index"] not in usable; assert reasons["writes_outside_its_frame"] not in usable; assert reasons["breaks_what_it_preserves"] not in usable; assert reasons["unframed_widened"] == "contract-verified-widened-state"; assert reasons["caller_must_lose_the_fact"] not in usable'
rejected_widened_state_summary_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_widened_state_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unproven obligation still exported a summary\n' >&2
    exit 1
fi

# A ternary arm, an unrecognized shape, and a guard whose fact names the same impure call as a
# later obligation are each refused; two calls of one impure function are not one term. The `and`
# and `or` operands are admitted instead, and establish nothing when skipped.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; unsupported = {name for kind, name in findings if kind == "expression-unsupported"}; assert {"conditional_call", "literal_field_call"} <= unsupported; assert "right_of_and" not in unsupported; assert "right_of_or" not in unsupported; assert ("index-upper-unproven", "bound_after_guard") in findings; assert ("index-upper-unproven", "stored_before_guard") in findings; assert not any(goal["proven"] and goal["rule"] == "index-upper" for goal in report["goals"])'
rejected_condition_call_positions_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_condition_call_positions_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a skippable or repeated impure call entered a proof state\n' >&2
    exit 1
fi

# `--proof <id>` renders one goal as an Elisa-like proof. The block keyword carries the verdict and
# only `proof ... qed` means the kernel checked it, so a goal that is unproven, or proven without a
# replayed certificate, must never render one.
proof_render_dir="$(mktemp -d)"
trap 'rm -rf "$proof_render_dir"' EXIT
set +e
proved_goal=$("$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); print(next(index for index, goal in enumerate(report["goals"]) if goal["rule"] == "index-upper" and goal["proven"]))')
"$ROOT_DIR/build/elisa-proof" --proof "$proved_goal" "$ROOT_DIR/examples/condition_call_positions.elisa" > "$proof_render_dir/proved.txt"
proof_render_proved_status=$?
open_goal=$("$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); print(next(index for index, goal in enumerate(report["goals"]) if not goal["proven"]))')
"$ROOT_DIR/build/elisa-proof" --proof "$open_goal" "$ROOT_DIR/examples/rejected_condition_call_positions.elisa" > "$proof_render_dir/open.txt"
proof_render_open_status=$?
"$ROOT_DIR/build/elisa-proof" --proof 99999 "$ROOT_DIR/examples/condition_call_positions.elisa" > "$proof_render_dir/missing.txt"
proof_render_missing_status=$?
set -e
if [[ "$proof_render_proved_status" -ne 0 || "$proof_render_open_status" -ne 0 || "$proof_render_missing_status" -ne 2 ]]; then
    printf 'proof test matrix failed: --proof exit codes proved=%s open=%s missing=%s\n' "$proof_render_proved_status" "$proof_render_open_status" "$proof_render_missing_status" >&2
    exit 1
fi
set +e
python3 - "$proof_render_dir/proved.txt" "$proof_render_dir/open.txt" "$proof_render_dir/missing.txt" <<'PY'
import sys

proved, open_goal, missing = (open(path, encoding="utf-8").read() for path in sys.argv[1:])
assert proved.startswith("# elisa-proof-proof-v1\n")
assert "\nproof guarded_index_" in proved
assert "\nqed\n" in proved
assert "    show index < values.count\n" in proved
assert "    by kernel certificate " in proved
assert "    given index < values.count" in proved
assert "branch-condition" in proved
assert "\nopen " in open_goal
assert "proof " not in open_goal.replace("elisa-proof-proof-v1", "")
assert "qed" not in open_goal
assert "    unproved: index-upper-unproven" in open_goal
assert "does not exist" in missing
assert "qed" not in missing and "\nproof " not in missing
PY
proof_render_shape_status=$?
set -e
if [[ "$proof_render_shape_status" -ne 0 ]]; then
    printf 'proof test matrix failed: --proof rendering shape\n' >&2
    exit 1
fi

# `--check-proof` reads a rendered block back and checks it against the source it names. The file is
# untrusted input: an edited keyword, an invented hypothesis, a swapped conclusion or a block from
# another source must all diverge, and a block naming no goal of this source cannot be checked.
set +e
"$ROOT_DIR/build/elisa-proof" --check-proof "$proof_render_dir/proved.txt" "$ROOT_DIR/examples/condition_call_positions.elisa" > "$proof_render_dir/faithful.json"
proof_check_faithful_status=$?
python3 -c 'import sys; text = open(sys.argv[1], encoding="utf-8").read(); open(sys.argv[2], "w", encoding="utf-8").write(text.replace("    show ", "    given values.count > 1000\n    show ", 1))' "$proof_render_dir/proved.txt" "$proof_render_dir/extra_given.txt"
"$ROOT_DIR/build/elisa-proof" --check-proof "$proof_render_dir/extra_given.txt" "$ROOT_DIR/examples/condition_call_positions.elisa" > "$proof_render_dir/extra_given.json"
proof_check_extra_status=$?
python3 -c 'import sys; text = open(sys.argv[1], encoding="utf-8").read(); lines = [line for line in text.splitlines() if not line.startswith("    unproved:")]; lines = [line.replace("open ", "proof ", 1) if line.startswith("open ") else line for line in lines]; lines.append("qed"); open(sys.argv[2], "w", encoding="utf-8").write("\n".join(lines) + "\n")' "$proof_render_dir/open.txt" "$proof_render_dir/forged.txt"
"$ROOT_DIR/build/elisa-proof" --check-proof "$proof_render_dir/forged.txt" "$ROOT_DIR/examples/rejected_condition_call_positions.elisa" > "$proof_render_dir/forged.json"
proof_check_forged_status=$?
"$ROOT_DIR/build/elisa-proof" --check-proof "$proof_render_dir/proved.txt" "$ROOT_DIR/examples/writable_lend_calls.elisa" > "$proof_render_dir/foreign.json"
proof_check_foreign_status=$?
printf 'not a proof block\n' > "$proof_render_dir/junk.txt"
"$ROOT_DIR/build/elisa-proof" --check-proof "$proof_render_dir/junk.txt" "$ROOT_DIR/examples/condition_call_positions.elisa" > "$proof_render_dir/junk.json"
proof_check_junk_status=$?
set -e
if [[ "$proof_check_faithful_status" -ne 0 || "$proof_check_extra_status" -ne 1 || "$proof_check_forged_status" -ne 1 || "$proof_check_foreign_status" -ne 1 || "$proof_check_junk_status" -ne 2 ]]; then
    printf 'proof test matrix failed: --check-proof exit codes faithful=%s extra=%s forged=%s foreign=%s junk=%s\n' "$proof_check_faithful_status" "$proof_check_extra_status" "$proof_check_forged_status" "$proof_check_foreign_status" "$proof_check_junk_status" >&2
    exit 1
fi
set +e
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

directory = sys.argv[1]
def load(name):
    with open(os.path.join(directory, name), encoding="utf-8") as handle:
        return json.load(handle)

faithful = load("faithful.json")
assert faithful["format"] == "elisa-proof-proof-check-v1"
assert faithful["status"] == "matches"
assert faithful["difference_count"] == 0 and faithful["differences"] == []
extra = load("extra_given.json")
assert extra["status"] == "diverges" and extra["difference_count"] > 0
assert any(entry["found"] == "    given values.count > 1000" for entry in extra["differences"])
forged = load("forged.json")
assert forged["status"] == "diverges"
assert any(entry["found"].startswith("proof ") and entry["expected"].startswith("open ") for entry in forged["differences"])
assert any(entry["found"] == "qed" for entry in forged["differences"])
foreign = load("foreign.json")
assert foreign["status"] == "diverges"
junk = load("junk.json")
assert junk["status"] == "unreadable" and junk["goal_id"] is None
PY
proof_check_shape_status=$?
set -e
if [[ "$proof_check_shape_status" -ne 0 ]]; then
    printf 'proof test matrix failed: --check-proof divergence reporting\n' >&2
    exit 1
fi

# `--script` is a text front end onto the checked tactic engine: it translates a human-written
# script into the same interchange a JSON script uses and gains no path of its own, so the two must
# produce byte-identical verdicts. The elaboration decides nothing — an unknown action, an
# unrecognized line, and a script with no steps must each be refused, and `qed` carries no weight.
set +e
"$ROOT_DIR/build/elisa-proof" --script "$ROOT_DIR/examples/proof_script_target.proof" "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/script_text.json"
proof_script_text_status=$?
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target.json" "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/script_json.json"
proof_script_json_status=$?
set -e
if [[ "$proof_script_text_status" -ne 0 || "$proof_script_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: proof script exit codes text=%s json=%s\n' "$proof_script_text_status" "$proof_script_json_status" >&2
    exit 1
fi
if ! cmp -s "$proof_render_dir/script_text.json" "$proof_render_dir/script_json.json"; then
    printf 'proof test matrix failed: a text proof script did not match its JSON equivalent\n' >&2
    exit 1
fi
printf '# goal 7\nproof p:\n    by nosuchtactic\nqed\n' > "$proof_render_dir/unknown_action.proof"
printf '# goal 7\nproof p:\n    bye assumption\nqed\n' > "$proof_render_dir/bad_line.proof"
printf '# goal 7\nproof p:\nqed\n' > "$proof_render_dir/no_steps.proof"
printf '# goal 7\nproof p:\n    by intro\nqed\n' > "$proof_render_dir/wrong_step.proof"
set +e
for refused_script in unknown_action bad_line no_steps wrong_step; do
    "$ROOT_DIR/build/elisa-proof" --script "$proof_render_dir/$refused_script.proof" "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/$refused_script.json"
done
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

directory = sys.argv[1]
for name in ("unknown_action", "bad_line", "no_steps", "wrong_step"):
    with open(os.path.join(directory, name + ".json"), encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["status"] != "proved", name
    assert not payload["tactic"]["valid"], name
    assert not payload["tactic"]["solved"], name
with open(os.path.join(directory, "script_text.json"), encoding="utf-8") as handle:
    admitted = json.load(handle)
assert admitted["status"] == "proved"
assert admitted["tactic"]["solved"] and admitted["tactic"]["kernel_replayed"]
assert admitted["source_goal_binding"]["bound"] and admitted["source_goal_binding"]["goal_id"] == 7
PY
proof_script_shape_status=$?
set -e
if [[ "$proof_script_shape_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a malformed proof script was admitted\n' >&2
    exit 1
fi

# `--repair` searches a bounded, fixed vocabulary of tactic scripts and admits one only if the
# checked engine solves the goal and the kernel replays the certificate it produced. The proposal
# it emits must itself run: a repair that cannot be re-checked is a claim, not a proof.
set +e
"$ROOT_DIR/build/elisa-proof" --repair 7 "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/repair.json"
proof_repair_status=$?
"$ROOT_DIR/build/elisa-proof" --repair 7 "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/repair_again.json"
"$ROOT_DIR/build/elisa-proof" --repair 9999 "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/repair_missing.json"
proof_repair_missing_status=$?
for unrepairable_goal in 1 3 5; do
    "$ROOT_DIR/build/elisa-proof" --repair "$unrepairable_goal" "$ROOT_DIR/examples/rejected_repair_target.elisa" > "$proof_render_dir/unrepaired_$unrepairable_goal.json"
    if [[ $? -ne 1 ]]; then
        printf 'proof test matrix failed: --repair did not report goal %s as unrepaired\n' "$unrepairable_goal" >&2
        exit 1
    fi
done
set -e
if [[ "$proof_repair_status" -ne 0 || "$proof_repair_missing_status" -ne 2 ]]; then
    printf 'proof test matrix failed: --repair exit codes repaired=%s missing=%s\n' "$proof_repair_status" "$proof_repair_missing_status" >&2
    exit 1
fi
if ! cmp -s "$proof_render_dir/repair.json" "$proof_render_dir/repair_again.json"; then
    printf 'proof test matrix failed: --repair is not deterministic\n' >&2
    exit 1
fi
python3 -c 'import json, sys; payload = json.load(open(sys.argv[1], encoding="utf-8")); assert payload["status"] == "repaired"; open(sys.argv[2], "w", encoding="utf-8").write(payload["script"])' "$proof_render_dir/repair.json" "$proof_render_dir/repair.proof"
set +e
"$ROOT_DIR/build/elisa-proof" --script "$proof_render_dir/repair.proof" "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/repair_rerun.json"
proof_repair_rerun_status=$?
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

directory = sys.argv[1]
def load(name):
    with open(os.path.join(directory, name), encoding="utf-8") as handle:
        return json.load(handle)

repaired = load("repair.json")
assert repaired["format"] == "elisa-proof-repair-v1"
assert repaired["status"] == "repaired" and repaired["script"]
assert repaired["search"]["tried"] >= 1 and repaired["search"]["candidates"] >= repaired["search"]["tried"]
rerun = load("repair_rerun.json")
assert rerun["status"] == "proved"
assert rerun["tactic"]["solved"] and rerun["tactic"]["kernel_replayed"] and rerun["tactic"]["certificate_replayed"]
missing = load("repair_missing.json")
assert missing["status"] == "not_found" and missing["script"] is None
for goal_id in (1, 3, 5):
    payload = load("unrepaired_%d.json" % goal_id)
    assert payload["status"] == "unrepaired", goal_id
    assert payload["script"] is None, goal_id
    assert payload["search"]["exhaustive"] is True, goal_id
    assert payload["search"]["tried"] == payload["search"]["candidates"], goal_id
PY
proof_repair_shape_status=$?
set -e
if [[ "$proof_repair_rerun_status" -ne 0 || "$proof_repair_shape_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a repaired script did not re-check (rerun=%s shape=%s)\n' "$proof_repair_rerun_status" "$proof_repair_shape_status" >&2
    exit 1
fi

# `--repair-all` walks the unresolved goals of a whole file in one pass. It repairs nothing the
# checker already proved, reports each open goal separately, and its verdict is the conjunction of
# the per-goal ones — a file with any unrepaired goal is `partial` and exits non-zero.
set +e
"$ROOT_DIR/build/elisa-proof" --repair-all "$ROOT_DIR/examples/verified.elisa" > "$proof_render_dir/batch_clean.json"
proof_batch_clean_status=$?
"$ROOT_DIR/build/elisa-proof" --repair-all "$ROOT_DIR/examples/rejected_repair_target.elisa" > "$proof_render_dir/batch_open.json"
proof_batch_open_status=$?
set -e
if [[ "$proof_batch_clean_status" -ne 0 || "$proof_batch_open_status" -ne 1 ]]; then
    printf 'proof test matrix failed: --repair-all exit codes clean=%s open=%s\n' "$proof_batch_clean_status" "$proof_batch_open_status" >&2
    exit 1
fi
set +e
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

directory = sys.argv[1]
def load(name):
    with open(os.path.join(directory, name), encoding="utf-8") as handle:
        return json.load(handle)

clean = load("batch_clean.json")
assert clean["format"] == "elisa-proof-repair-batch-v1"
assert clean["status"] == "nothing_to_repair"
assert clean["summary"]["unresolved"] == 0 and clean["summary"]["repaired"] == 0
assert clean["goals"] == []
open_file = load("batch_open.json")
assert open_file["status"] == "partial"
assert open_file["summary"]["unresolved"] == 3 and open_file["summary"]["repaired"] == 0
assert {entry["goal_id"] for entry in open_file["goals"]} == {1, 3, 5}
assert {entry["name"] for entry in open_file["goals"]} == {"unrelated_hypothesis", "wrong_direction", "needs_arithmetic_we_do_not_have"}
for entry in open_file["goals"]:
    assert entry["status"] == "unrepaired" and entry["script"] is None
    assert entry["tried"] == open_file["summary"]["candidates"]
PY
proof_batch_shape_status=$?
set -e
if [[ "$proof_batch_shape_status" -ne 0 ]]; then
    printf 'proof test matrix failed: --repair-all reporting\n' >&2
    exit 1
fi

# An unpinned lifetime and a region value reaching a formal that declares none are each refused.
set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_region_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("region-call-opaque", "unpinned_formal") in findings; assert ("region-call-opaque", "unmapped_lifetime") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_region_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_region_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unpinned lifetime was lent\n' >&2
    exit 1
fi

if [[ "$rejected_shared_borrow_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an escaping, moved or exclusively borrowed capability was lent without a summary\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_budget.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; assert {f["name"]: f["status"] for f in report["findings"]} == {"too_wide_quantifier": "timeout", "too_large_model": "timeout", "unsupported_reasoning": "unknown", "false_comparison": "disproved", "too_many_congruence_terms": "timeout", "too_many_congruence_rounds": "timeout", "too_many_disjunctions": "timeout", "too_deep_conditional": "timeout"}'
rejected_budget_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_budget_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exhausted, undecided and refuted goals were not reported as distinct states\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --goal 1 "$ROOT_DIR/examples/rejected_budget.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "timeout"; assert report["failure"]["status"] == "timeout"; assert report["failure"]["counterexample_found"] is False'
budget_goal_status=${PIPESTATUS[1]}
if [[ "$budget_goal_status" -ne 0 ]]; then
    printf 'proof test matrix failed: the focused-goal API did not report an exhausted search as a timeout\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/effect_containment.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; certified = {g["name"] for g in report["goals"] if g["rule"] == "effect-containment"}; assert {"wider_row", "union_row", "exact_row", "no_calls", "calls_rowless"} <= certified; rows = {d["name"]: d["effects"] for d in report["declaration_details"] if d["kind"] == "function"}; assert rows["exact_row"] == ["Memory.Allocate"]; assert rows["pure_callee"] is None'
effect_containment_status=${PIPESTATUS[1]}
if [[ "$effect_containment_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a containable declared effect row was not imported or certified\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_effect_containment.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; certified = {g["name"] for g in report["goals"] if g["rule"] == "effect-containment"}; assert not (certified & {"narrower_than_callee", "one_uncovered_callee", "opaque_callee"}); kinds = {f["name"]: (f["kind"], f["status"]) for f in report["findings"]}; assert kinds["narrower_than_callee"] == ("effect-row-exceeded", "disproved"); assert kinds["opaque_callee"] == ("effect-call-opaque", "unsupported")'
rejected_effect_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_effect_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an uncontained or unresolved effect row was certified\n' >&2
    exit 1
fi

# A megabyte of source must produce a verdict rather than a stack overflow. The tool used to die
# on anything past roughly half a megabyte, which is less than `src/proof/check.elisa` itself: a
# declaration whose initializer is a conditional expression, inside a captured loop body, leaks
# stack on every iteration in the compiler this is built with, and the include expander read one
# byte per iteration through exactly that shape. The generated file is plain and large on purpose;
# what is under test is that the size is survivable, not what it proves.
large_source_dir="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-large.XXXXXX")"
python3 - "$large_source_dir/large.elisa" <<'PY'
import sys
(path,) = sys.argv[1:]
line = "# " + "x" * 78 + "\n"
with open(path, "w", encoding="utf-8") as handle:
    handle.write("def large_source_is_survivable() -> i64:\n    ensure result == 1\n    return 1\n")
    handle.write(line * (1024 * 1024 // len(line)))
PY
"$ROOT_DIR/build/elisa-proof" --json "$large_source_dir/large.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert ("large_source_is_survivable", "goal") in {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}'
large_source_status=${PIPESTATUS[1]}
rm -rf "$large_source_dir"
if [[ "$large_source_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a megabyte of source did not produce a verdict\n' >&2
    exit 1
fi

printf 'proof test matrix passed: accepted examples exit 0; rejected example exits 1\n'
