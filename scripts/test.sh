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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/kernel_replay_standalone.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] >= 25; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; declarations = {declaration["name"] for declaration in report["declaration_details"] if declaration["kind"] == "function" and declaration["verified"]}; required = {"proof_kernel_replay_node_at", "proof_kernel_replay_bool_at", "proof_kernel_replay_bool_set", "proof_kernel_replay_child_at", "proof_kernel_replay_child_range_valid", "proof_kernel_replay_arena_shape_valid", "proof_kernel_replay_arena_child_kind_valid", "proof_kernel_replay_difference_query", "proof_kernel_replay_model_value_at"}; assert required <= declarations; assert report["trust"]["trusted_assumptions"] == []'
kernel_replay_standalone_probe_status=${PIPESTATUS[1]}
if [[ "$kernel_replay_standalone_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: standalone replay audit has certificate gaps\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["source"]["bytes"] > 0; assert report["source"]["fingerprint"]["algorithm"] == "fnv1a32"; assert 0 <= report["source"]["fingerprint"]["value"] < 2**32; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert len(report["certificates"]) == report["replay"]["certificates"]; assert report["repair_queue"] == []; assert report["trust"]["trusted_assumptions"] == []; assert report["replay"]["gaps"] == 0; assert report["kernel"]["format"] == "elisa-proof-kernel-v1"; assert report["kernel"]["independent_replay"] is True; assert len(report["kernel"]["nodes"]) > 0; assert report["action_protocol"]["format"] == "elisa-proof-tactics-v1"; assert report["action_protocol"]["admission"] == "kernel-backed"; assert report["action_protocol"]["operations"] == ["assumption", "exact", "decide", "intro", "apply", "simp", "have", "instantiate", "rewrite", "split", "left", "right", "cases"]; assert report["action_protocol"]["branch_script"]["nested"] is True; assert report["action_protocol"]["branch_script"]["max_branch_depth"] == 32'
json_probe_status=$?
if [[ "$json_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: JSON report is not a valid structured proof state\n' >&2
    exit 1
fi
for replay_fixture in replay_constant arithmetic_identity equality_alias quantifier collection_quantifier quantifier_structural_terms difference_constraints disjunctive_facts modulo_division_bounds proof_step_derivation pattern_proof pattern_or pinned_pattern pattern_scalar_literals total_match value_match value_match_nested_pure_call bounded_model loop_range_facts for_invariant for_loop_control_invariant indexed_frame slice_bounds slice_kernel indexn_kernel indexn_call_summary pure_index_call index_call_summary slice_call_summary fixed_array_bounds fixed_array_slice_bounds checked_index_fallback getelse_recovery getelse_checked_index getelse_call getelse_loop_control getelse_raise catch_expression catch_nested_pure_arm_call loop_control_invariant continue_decreases continue_decreases_branch shorthand_member constructor_kernel dogfood_kernel dogfood_kernel_core region_allocation region_statement region_auto_close region_new_call_argument region_new_mutable_call_argument; do
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/region_statement.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert kinds.count("resource-region-open") == 1 and kinds.count("resource-region-close") == 1 and "resource-region-alloc" in kinds and "resource-region-bind" in kinds and "resource-region-alloc-discard" in kinds'
region_statement_probe_status=${PIPESTATUS[1]}
if [[ "$region_statement_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: canonical region statement transitions were not replayed\n' >&2
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/slice_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 9; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert "slice" in kinds; assert "absent" in kinds'
slice_kernel_probe_status=${PIPESTATUS[1]}
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/quantifier_structural_terms.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 6; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert {"quantifier", "array", "if", "construct", "field-init"} <= kinds'
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

"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/implicit_structural_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0'
implicit_structural_status=${PIPESTATUS[1]}
if [[ "$implicit_structural_status" -ne 0 ]]; then
    printf 'proof test matrix failed: implicit structural termination\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/inferred_product_structural_decreases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0'
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/dogfood_kernel_core.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["declarations"] == 9; assert report["summary"]["obligations"] == 20; assert report["replay"]["gaps"] == 0; assert [goal["goal_id"] for goal in report["goals"]] == list(range(len(report["goals"]))); assert [certificate["certificate_id"] for certificate in report["certificates"]] == list(range(len(report["certificates"]))); assert all(goal["certificate_id"] is not None for goal in report["goals"]); assert all(goal["certificate_id"] < len(report["certificates"]) for goal in report["goals"])'
dogfood_core_contract_probe_status=${PIPESTATUS[1]}
if [[ "$dogfood_core_contract_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: direct calls to dogfood kernel contracts\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/src/proof/kernel_core.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["obligations"] == 7; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["kernel"]["independent_replay"] is True'
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/captured_structural_accumulator.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); assert not any(finding["kind"] == "structural-decreases-unproven" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
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
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_borrow_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "borrow-call-opaque" and finding["status"] == "unsupported" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
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

if [[ "$verified_status" -ne 0 || "$include_status" -ne 0 || "$lemma_status" -ne 0 || "$recursive_lemma_status" -ne 0 || "$mutual_recursive_lemmas_status" -ne 0 || "$lexicographic_recursive_lemma_status" -ne 0 || "$summary_status" -ne 0 || "$framed_call_status" -ne 0 || "$header_frame_status" -ne 0 || "$branch_negation_status" -ne 0 || "$old_state_status" -ne 0 || "$structured_result_status" -ne 0 || "$assert_by_local_status" -ne 0 || "$pattern_status" -ne 0 || "$arithmetic_identity_status" -ne 0 || "$equality_alias_status" -ne 0 || "$quantifier_status" -ne 0 || "$void_postcondition_status" -ne 0 || "$named_arguments_status" -ne 0 || "$default_arguments_status" -ne 0 || "$assignment_rhs_state_status" -ne 0 || "$pure_contract_call_status" -ne 0 || "$recursive_pure_contract_call_status" -ne 0 || "$pure_default_contract_call_status" -ne 0 || "$mutual_recursive_pure_contract_call_status" -ne 0 || "$recursive_decreases_status" -ne 0 || "$mutual_decreases_status" -ne 0 || "$move_runtime_status" -ne 0 || "$rejected_status" -ne 1 || "$rejected_lemma_status" -ne 1 || "$self_assert_status" -ne 1 || "$overflow_status" -ne 1 || "$stale_branch_status" -ne 1 || "$fallthrough_status" -ne 1 || "$invariant_status" -ne 1 || "$rejected_for_invariant_status" -ne 1 || "$rejected_for_invariant_scope_status" -ne 1 || "$call_precondition_status" -ne 1 || "$lemma_result_status" -ne 1 || "$compound_assignment_status" -ne 1 || "$frame_write_status" -ne 1 || "$frame_preserve_status" -ne 1 || "$frame_call_status" -ne 1 || "$header_frame_rejected_status" -ne 1 || "$header_frame_root_rejected_status" -ne 1 || "$frame_condition_status" -ne 1 || "$frame_alias_status" -ne 1 || "$old_call_status" -ne 1 || "$quantifier_rejected_status" -ne 1 || "$void_postcondition_rejected_status" -ne 1 || "$named_arguments_rejected_status" -ne 1 || "$default_arguments_rejected_status" -ne 1 || "$assert_call_stale_status" -ne 1 || "$assert_by_call_stale_status" -ne 1 || "$decreases_rejected_status" -ne 1 || "$recursive_summary_rejected_status" -ne 1 || "$recursive_decreases_rejected_status" -ne 1 || "$recursive_assert_rejected_status" -ne 1 || "$recursive_lemma_rejected_status" -ne 1 || "$recursive_lemma_decreases_rejected_status" -ne 1 ]]; then
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
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target_nested_branch.json" "$ROOT_DIR/examples/verified_branch.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["source_goal_binding"] == {"bound": True, "goal_id": 1}; assert report["tactic"]["certificate_replayed"] is True; assert report["branches"]["left"]["branches"]["right"]["solved"] is True'
source_nested_branch_status=${PIPESTATUS[0]}
if [[ "$source_nested_branch_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound nested branch tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["source_goal_binding"] == {"bound": True, "goal_id": 7}; assert report["tactic"]["status"] == "proved"; assert len(report["state"]["initial_facts"]) == 1'
source_bound_script_status=${PIPESTATUS[0]}
if [[ "$source_bound_script_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound tactic script\n' >&2
    exit 1
fi

printf 'proof test matrix passed: accepted examples exit 0; rejected example exits 1\n'
