# shellcheck shell=bash
# Part 9 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
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
run_json_report "$ROOT_DIR/examples/rejected_region_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("region-call-opaque", "unpinned_formal") in findings; assert ("region-call-opaque", "unmapped_lifetime") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
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
run_json_report "$ROOT_DIR/examples/rejected_budget.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; assert {f["name"]: f["status"] for f in report["findings"]} == {"too_wide_quantifier": "timeout", "too_large_model": "timeout", "unsupported_reasoning": "unknown", "false_comparison": "disproved", "too_many_congruence_terms": "timeout", "too_many_congruence_rounds": "timeout", "too_many_disjunctions": "timeout", "too_deep_conditional": "timeout", "too_deep_disjunctive_goal": "timeout"}'
rejected_budget_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_budget_status" -ne 0 ]]; then
    printf 'proof test matrix failed: exhausted, undecided and refuted goals were not reported as distinct states\n' >&2
    exit 1
fi

# A certified cancellation replays its ground form only where the width guards decided every step.
set +e
run_json_report "$ROOT_DIR/examples/rejected_normalized_ground_difference.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"]}; assert reasons == {"unsigned_cancellation_wraps": "body-unverified", "unbounded_signed_cancellation": "body-unverified", "bounded_signed_cancellation": "verified"}, reasons'
normalized_ground_difference_status=${PIPESTATUS[1]}
set -e
if [[ "$normalized_ground_difference_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a ground difference replayed outside its width guards\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --goal 1 "$ROOT_DIR/examples/rejected_budget.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "timeout"; assert report["failure"]["status"] == "timeout"; assert report["failure"]["counterexample_found"] is False'
budget_goal_status=${PIPESTATUS[1]}
if [[ "$budget_goal_status" -ne 0 ]]; then
    printf 'proof test matrix failed: the focused-goal API did not report an exhausted search as a timeout\n' >&2
    exit 1
fi

run_json_report "$ROOT_DIR/examples/effect_containment.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; certified = {g["name"] for g in report["goals"] if g["rule"] == "effect-containment"}; assert {"wider_row", "union_row", "exact_row", "no_calls", "calls_rowless"} <= certified; rows = {d["name"]: d["effects"] for d in report["declaration_details"] if d["kind"] == "function"}; assert rows["exact_row"] == ["Memory.Allocate"]; assert rows["pure_callee"] is None'
effect_containment_status=${PIPESTATUS[1]}
if [[ "$effect_containment_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a containable declared effect row was not imported or certified\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_effect_containment.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; certified = {g["name"] for g in report["goals"] if g["rule"] == "effect-containment"}; assert not (certified & {"narrower_than_callee", "one_uncovered_callee", "opaque_callee"}); kinds = {f["name"]: (f["kind"], f["status"]) for f in report["findings"]}; assert kinds["narrower_than_callee"] == ("effect-row-exceeded", "disproved"); assert kinds["opaque_callee"] == ("effect-call-opaque", "unsupported")'
rejected_effect_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_effect_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an uncontained or unresolved effect row was certified\n' >&2
    exit 1
fi

# Internal proof witnesses and generated rebind symbols share the ordinary identifier AST node.
# A source declaration in that namespace must be rejected before it can counterfeit a compiler
# type witness or collide with a fresh proof-state name.
set +e
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/reserved-proof-name.o" "$ROOT_DIR/examples/rejected_forged_unsigned_marker.elisa" >/dev/null 2>&1
reserved_source_compiler_status=$?
run_json_report "$ROOT_DIR/examples/rejected_forged_unsigned_marker.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert report["summary"]["proven"] == 0; assert report["replay"]["gaps"] == 0; assert report["findings"] == [{"kind": "proof-internal-name", "status": "unsupported", "line": 2, "file": 0, "file_line": 2, "name": "__elisa_unsigned_type_bound", "message": "source identifier collides with a proof-system internal name", "counterexample_found": False, "goal_id": None, "counterexample": []}]'
reserved_marker_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_rebind_symbol_collision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert report["summary"]["proven"] == 0; assert report["replay"]["gaps"] == 0; assert report["findings"][0]["kind"] == "proof-internal-name"; assert report["findings"][0]["name"] == "__elisa_rebind_0"; assert report["findings"][0]["line"] == 5'
reserved_rebind_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/internal_prefix_noncollision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["verification_state"] == "proved"; assert report["replay"]["gaps"] == 0; assert not report["findings"]'
reserved_noncollision_status=${PIPESTATUS[1]}
set -e
if [[ "$reserved_source_compiler_status" -ne 0 || "$reserved_marker_status" -ne 0 || "$reserved_rebind_status" -ne 0 || "$reserved_noncollision_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source code collided with a proof-system internal name\n' >&2
    exit 1
fi

# An include graph may legitimately expand to an empty source file. The importer must pass that
# successful zero-byte expansion to the parser instead of falling back to the root include line.
set +e
run_json_report "$ROOT_DIR/examples/import_empty_root.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["source"]["bytes"] == 0; assert report["replay"]["gaps"] == 0; assert report["findings"] == []'
empty_import_status=${PIPESTATUS[1]}
set -e
if [[ "$empty_import_status" -ne 0 ]]; then
    printf 'proof test matrix failed: successful empty include expansion was not preserved\n' >&2
    exit 1
fi

if "$ROOT_DIR/build/elisa-proof" --unknown-option "$ROOT_DIR/examples/verified.elisa" >/dev/null 2>&1; then
    printf 'proof test matrix failed: unknown CLI option was accepted\n' >&2
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
# Compiler 8e08cd33 Stage1 reports AutoRegionStoreEscape (kind code 620) for this escaping local-reference call.
run_json_report "$ROOT_DIR/examples/rejected_collection_builtin_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; semantic = [(d["kind_code"], d["line"], d["name"]) for d in report.get("semantic_diagnostics", []) if d["severity"] == 1]; assert semantic == [(620, 15, "grow")], semantic; assert report["summary"]["semantic_errors"] == 1; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"borrow-call-summary-unsupported", "ensure-unproven", "index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_lend_still_escapes"] == "body-unverified"; assert reasons["a_push_in_the_body_still_writes"] == "body-unverified"; assert reasons["a_push_still_changes_the_count"] == "body-unverified"; assert reasons["a_pushed_lend_still_escapes"] == "body-unverified"'
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
run_json_report "$ROOT_DIR/examples/rejected_global_constant_collision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "disproved"; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong" and f["status"] == "disproved" and f["counterexample_found"] and f["counterexample"] == [] for f in report["findings"])'
rejected_global_constant_collision_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_global_constant_usize_collision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(f["kind"] == "ensure-unproven" and f["name"] == "wrong" and f["status"] == "unknown" and not f["counterexample_found"] for f in report["findings"])'
rejected_global_constant_usize_collision_status=${PIPESTATUS[1]}
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_global_constant_function_collision.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "disproved"; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(f["kind"] == "ensure-unproven" and f["name"] == "check" and f["line"] == 14 and f["status"] == "disproved" and f["counterexample_found"] and f["counterexample"] == [] for f in report["findings"]); assert len(report["findings"]) == 1; checks = {item["line"]: item["verified"] for item in report["declaration_details"] if item["kind"] == "function" and item["name"] == "check"}; assert checks == {6: True, 12: False}'
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
