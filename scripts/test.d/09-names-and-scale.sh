# shellcheck shell=bash
# Part 9 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
python3 - "$large_source_dir/large.elisa" <<'PY'
import sys
(path,) = sys.argv[1:]
line = "# " + "x" * 78 + "\n"
with open(path, "w", encoding="utf-8") as handle:
    handle.write("def large_source_is_survivable() -> i64:\n    ensure result == 1\n    return 1\n")
    handle.write(line * (1024 * 1024 // len(line)))
PY
run_json_report "$large_source_dir/large.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert ("large_source_is_survivable", "goal") in {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}'
large_source_status=${PIPESTATUS[1]}
rm -rf "$large_source_dir"
if [[ "$large_source_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a megabyte of source did not produce a verdict\n' >&2
    exit 1
fi

# A method call's receiver is not among its arguments, so the frame records it by name. A collection
# builtin writes its receiver during its own call and leaves nothing a later call could reach, so it
# is not part of what escapes -- otherwise a list this frame only pushed to stayed aliased forever
# and every loop over its `count` lost its range. The write itself, and every other route out, stay.
set +e
run_json_report "$ROOT_DIR/examples/collection_builtin_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"push_then_loop", "shrink_then_loop", "two_collections"}'
collection_builtin_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$collection_builtin_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a collection only pushed to still lost its loop range\n' >&2
    exit 1
fi

set +e
# Compiler 2678ff10 itself rejects grow(&items, sink) as storing a local reference (semantic error 609).
run_json_report "$ROOT_DIR/examples/rejected_collection_builtin_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; semantic = [(d["kind_code"], d["line"], d["name"]) for d in report.get("semantic_diagnostics", []) if d["severity"] == 1]; assert semantic == [(609, 15, "grow")], semantic; assert report["summary"]["semantic_errors"] == 1; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"borrow-call-summary-unsupported", "ensure-unproven", "index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_lend_still_escapes"] == "body-unverified"; assert reasons["a_push_in_the_body_still_writes"] == "body-unverified"; assert reasons["a_push_still_changes_the_count"] == "body-unverified"; assert reasons["a_pushed_lend_still_escapes"] == "body-unverified"'
rejected_collection_builtin_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_collection_builtin_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a collection builtin laundered a reach it does not have\n' >&2
    exit 1
fi

# Module-local literal constants must remain available to replay, while a same-named constant in
# another namespace must not be flattened into the importing function's proof state.
set +e
run_json_report "$ROOT_DIR/examples/global_constant_module.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["verification_state"] == "proved"; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert not report["findings"]'
global_constant_module_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_global_constant_collision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong" and f["status"] == "unknown" and not f["counterexample_found"] for f in report["findings"])'
rejected_global_constant_collision_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_global_constant_usize_collision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong" and f["status"] == "unknown" and not f["counterexample_found"] for f in report["findings"])'
rejected_global_constant_usize_collision_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_global_constant_function_collision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(f["kind"] == "ensure-unproven" and f["name"] == "check" and f["line"] == 14 and f["status"] == "unknown" and not f["counterexample_found"] for f in report["findings"]); assert len(report["findings"]) == 1'
rejected_global_constant_function_collision_status=${PIPESTATUS[1]}
set -e
if [[ "$global_constant_module_status" -ne 0 || "$rejected_global_constant_collision_status" -ne 0 || "$rejected_global_constant_usize_collision_status" -ne 0 || "$rejected_global_constant_function_collision_status" -ne 0 ]]; then
    printf 'proof test matrix failed: module constant scope was not preserved through replay\n' >&2
    exit 1
fi
run_py_test test_module_u8_constant_contract.py

# A rebind written over the binding's own symbol takes a fresh symbol, so the new value is recorded
# and the old one keeps its facts. The equality that records it is admitted into the difference
# graph under the same increment argument the goal side already used: a strict peer of the same
# unsigned width puts `x + 1` in range. Neither the symbol nor the import may say more than that.
set +e
run_json_report "$ROOT_DIR/examples/loop_counter_invariant.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"bounded_counter", "walk_to_limit", "increment_keeps_its_value", "two_counters"}'
loop_counter_invariant_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_counter_invariant_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a counter lost its own value across its update\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_loop_counter_invariant.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"ensure-unproven", "invariant-not-preserved", "invariant-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["an_increment_without_a_peer"] == "body-unverified"; assert reasons["a_non_unit_step"] == "body-unverified"; assert reasons["a_false_invariant"] == "body-unverified"; assert reasons["a_counter_is_not_a_total"] == "body-unverified"; assert reasons["a_pre_update_fact_is_not_current"] == "body-unverified"'
rejected_loop_counter_invariant_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_counter_invariant_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fresh rebind symbol claimed more than the update\n' >&2
    exit 1
fi

# Equality on a user-defined struct dispatches to the protocol method. The method below mutates
# its receiver, so the caller cannot preserve the pre-comparison fact across either branch.
set +e
run_json_report "$ROOT_DIR/examples/rejected_operator_effect.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(f["kind"] == "expression-unsupported" and "unmodeled user protocol" in f["message"] for f in report["findings"])'
rejected_operator_effect_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_operator_effect_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an overloaded operator crossed a proof-state boundary\n' >&2
    exit 1
fi

# Keep the proof assistant reviewable and preserve the private/public module boundaries. This
# guard covers implementation source only; examples and long-form audit documentation are test
# fixtures and are intentionally allowed to be larger.
while IFS= read -r proof_source; do
    proof_lines=$(wc -l < "$proof_source")
    if [[ "$proof_lines" -gt 600 ]]; then
        printf 'proof source exceeds 600 lines: %s (%s)\n' "$proof_source" "$proof_lines" >&2
        exit 1
    fi
done < <(find "$ROOT_DIR/src" -type f -name '*.elisa' -print | sort)

set +e
run_json_report "$ROOT_DIR/examples/rejected_proposition_nesting.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] != "proved"; assert any(finding["kind"] == "contract-proposition-type" and finding["message"] == "kernel proposition statement nesting exceeded its bounded representation" for finding in report["findings"])'
proposition_nesting_status=("${PIPESTATUS[@]}")
set -e
if [[ "${proposition_nesting_status[0]}" -ne 1 || "${proposition_nesting_status[1]}" -ne 0 ]]; then
    printf 'proof test matrix failed: exhausted proposition formation did not record its failure\n' >&2
    exit 1
fi

"$ROOT_DIR/scripts/test_optimized_replay.sh"
python3 "$ROOT_DIR/scripts/census_diff.py"
if [[ "$keep_going_failures" -gt 0 ]]; then
    printf 'proof test matrix failed: %s step(s) failed (KEEP_GOING)\n' "$keep_going_failures" >&2
    builtin exit 1
fi
printf 'proof test matrix passed: accepted examples exit 0; rejected example exits 1\n'
