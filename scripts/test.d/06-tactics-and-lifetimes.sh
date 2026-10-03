# shellcheck shell=bash
# Part 6 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
# The i64-backed arena must neither decide a negative u64 bit pattern using signed order nor
# fold fixed-width unsigned arithmetic as unbounded signed arithmetic. Exercise both exact and
# simp tactic replay against their false claims; either accepting one would be a kernel soundness
# failure even if ordinary source analysis correctly reports the goal as unknown.
readonly REJECTED_U64_MAX_GOAL_ID=7
readonly REJECTED_U64_MAX_GOAL_FINGERPRINT=3748040360
readonly REJECTED_U8_OVERFLOW_GOAL_ID=13
readonly REJECTED_U8_OVERFLOW_GOAL_FINGERPRINT=1229197265
for tactic_fixture in rejected_u64_max_decide rejected_u8_overflow_decide rejected_u8_overflow_simp; do
    case "$tactic_fixture" in
        rejected_u64_max_decide)
            tactic_source_goal="$REJECTED_U64_MAX_GOAL_ID"
            tactic_goal_fingerprint="$REJECTED_U64_MAX_GOAL_FINGERPRINT"
            ;;
        rejected_u8_overflow_*)
            tactic_source_goal="$REJECTED_U8_OVERFLOW_GOAL_ID"
            tactic_goal_fingerprint="$REJECTED_U8_OVERFLOW_GOAL_FINGERPRINT"
            ;;
    esac
    tactic_report="$standalone_probe_dir/$tactic_fixture.json"
    set +e
    "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_$tactic_fixture.json" "$ROOT_DIR/examples/rejected_u64_max_conflict.elisa" >"$tactic_report"
    tactic_exit=$?
    set -e
    if [[ "$tactic_exit" -ne 1 ]] || ! python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); t=r["tactic"]; binding=r["source_goal_binding"]; assert r["status"] == "failed" and binding["goal_id"] == int(sys.argv[2]); assert binding["fingerprint_match"] is True and binding["goal_fingerprint"]["value"] == int(sys.argv[3]); assert t["valid"] is False and t["solved"] is False; assert t["reason"] == "tactic action outcome contradicted the script'"'"'s expected acceptance" and t["action_count"] == 1 and t["accepted_count"] == 0' "$tactic_report" "$tactic_source_goal" "$tactic_goal_fingerprint"; then
        printf 'proof test matrix failed: unsound unsigned tactic proof was accepted (%s)\n' "$tactic_fixture" >&2
        exit 1
    fi
    # The same action declared as refused must be a well-formed script that runs the tactic and
    # observes the refusal, so the rejection above cannot come from a malformed document.
    refused_script="$standalone_probe_dir/$tactic_fixture.refused.json"
    python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); [a.__setitem__("accepted", False) for a in s["actions"]]; json.dump(s, open(sys.argv[2], "w"))' "$ROOT_DIR/examples/tactic_script_$tactic_fixture.json" "$refused_script"
    refused_report="$standalone_probe_dir/$tactic_fixture.refused.report.json"
    set +e
    "$ROOT_DIR/build/elisa-proof" --tactics "$refused_script" "$ROOT_DIR/examples/rejected_u64_max_conflict.elisa" >"$refused_report"
    refused_exit=$?
    set -e
    if [[ "$refused_exit" -ne 1 ]] || ! python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); t=r["tactic"]; assert r["status"] == "failed"; assert t["valid"] is True and t["solved"] is False; assert t["action_count"] == 1 and t["accepted_count"] == 0' "$refused_report"; then
        printf 'proof test matrix failed: unsigned tactic refusal was not observed as a refused action (%s)\n' "$tactic_fixture" >&2
        exit 1
    fi
done

# A `u64`/`usize` literal above the i64 range keeps its recorded type through proof search, the
# kernel arena and replay: true orderings prove and replay, the orderings its wrapped payload
# would satisfy under signed order stay refused, and no refusal claims a counterexample.
set +e
run_json_report "$ROOT_DIR/examples/typed_unsigned_literals.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed" and report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0 and report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}; proved = {"u64_max_exceeds_zero", "u64_max_equals_itself", "u64_max_exceeds_high_bit", "usize_high_bit_at_least_small"}; refused = {"u64_max_is_not_below_zero", "u64_high_bit_is_not_below_max", "u64_max_is_not_zero", "untyped_wrapped_literal_is_not_ordered"}; assert all(functions[name]["verified"] for name in proved); assert not any(functions[name]["verified"] for name in refused); findings = {f["name"]: f for f in report["findings"] if f["kind"] == "ensure-unproven"}; assert set(findings) == refused; assert all(f["status"] == "unknown" and not f["counterexample_found"] for f in findings.values())'
typed_unsigned_status=${PIPESTATUS[1]}
set -e
if [[ "$typed_unsigned_status" -ne 0 ]]; then
    printf 'proof test matrix failed: typed high-bit unsigned literal comparison\n' >&2
    exit 1
fi
typed_goal_fingerprint() {
    "$ROOT_DIR/build/elisa-proof" --goal "$1" "$ROOT_DIR/examples/typed_unsigned_literals.elisa" \
        | python3 -c 'import json,sys; g=json.load(sys.stdin)["goal_fingerprint"]; assert g["algorithm"] == "fnv1a32-kernel-goal-v2"; print(g["value"])'
}
# Goal 1 is `0xFFFFFFFFFFFFFFFFu64 > 0u64` (true), goal 9 is `... < 0u64` (false). The
# script names the literal only by its source offset; the type comes from the source table.
for typed_goal in 1 9; do
    typed_script="$standalone_probe_dir/typed_unsigned_decide_$typed_goal.json"
    printf '{"format":"elisa-proof-tactics-v1","target":{"goal_id":%s,"goal_fingerprint":%s},"actions":[{"action":"decide"}]}' "$typed_goal" "$(typed_goal_fingerprint "$typed_goal")" >"$typed_script"
    set +e
    typed_result="$("$ROOT_DIR/build/elisa-proof" --tactics "$typed_script" "$ROOT_DIR/examples/typed_unsigned_literals.elisa")"
    set -e
    if ! printf '%s' "$typed_result" | python3 -c 'import json,sys; r=json.load(sys.stdin); t=r["tactic"]; assert r["source_goal_binding"]["fingerprint_match"] is True; expected = sys.argv[1] == "1"; assert t["valid"] is expected and t["solved"] is expected; assert (r["status"] == "proved") is expected; assert not expected or (t["kernel_replayed"] is True and t["certificate_replayed"] is True)' "$typed_goal"; then
        printf 'proof test matrix failed: typed unsigned decide tactic on goal %s\n' "$typed_goal" >&2
        exit 1
    fi
done
# Migration: the v1 fingerprint recorded for the u64 maximum goal before literals carried their
# type no longer binds, so a stale script cannot silently address the re-typed proposition.
stale_script="$standalone_probe_dir/typed_unsigned_stale_v1.json"
printf '{"format":"elisa-proof-tactics-v1","target":{"goal_id":7,"goal_fingerprint":515359733},"actions":[{"action":"decide","accepted":false}]}' >"$stale_script"
set +e
stale_result="$("$ROOT_DIR/build/elisa-proof" --tactics "$stale_script" "$ROOT_DIR/examples/rejected_u64_max_conflict.elisa")"
set -e
if ! printf '%s' "$stale_result" | python3 -c 'import json,sys; r=json.load(sys.stdin); b=r["source_goal_binding"]; assert r["status"] == "failed" and b["fingerprint_match"] is False and b["goal_fingerprint"]["algorithm"] == "fnv1a32-kernel-goal-v2"; assert r["tactic"]["reason"] == "target.goal_fingerprint does not match the imported kernel goal and hypotheses"'; then
    printf 'proof test matrix failed: a stale v1 goal fingerprint still bound a typed-literal goal\n' >&2
    exit 1
fi
# A literal offset is a u32 source position; any other spelling makes the script malformed. A
# portable script's offset names no source literal, so its wrapped payload stays undecidable.
for typed_offset in '-3' '"x"' '4294967296' '120'; do
    offset_script="$standalone_probe_dir/typed_unsigned_offset.json"
    printf '{"format":"elisa-proof-tactics-v1","initial":{"facts":[],"goal":{"kind":"binary","operator":">","left":{"kind":"int","value":-1,"line":6,"offset":%s},"right":{"kind":"int","value":0}}},"actions":[{"action":"decide","accepted":false}]}' "$typed_offset" >"$offset_script"
    set +e
    offset_result="$("$ROOT_DIR/build/elisa-proof" --tactics "$offset_script" "$ROOT_DIR/examples/verified.elisa")"
    set -e
    if ! printf '%s' "$offset_result" | python3 -c 'import json,sys; r=json.load(sys.stdin); t=r["tactic"]; assert r["status"] == "failed" and t["solved"] is False; assert t["valid"] is (sys.argv[1] == "120"); assert t["valid"] or t["reason"] == "invalid proof script"' "$typed_offset"; then
        printf 'proof test matrix failed: typed literal offset %s\n' "$typed_offset" >&2
        exit 1
    fi
done

# Safe small arithmetic remains available to tactics, and the independently replayed kernel
# must accept the same bottom-up simplification as the source tactic.
if ! "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_safe_small_constant_simp.json" "$ROOT_DIR/examples/replay_constant.elisa" \
    | python3 -c 'import json,sys; r=json.load(sys.stdin); t=r["tactic"]; assert r["status"] == "proved"; assert t["valid"] is True and t["solved"] is True; assert t["kernel_trace_replayed"] is True and t["certificate_replayed"] is True'; then
    printf 'proof test matrix failed: safe small-constant simp did not replay successfully\n' >&2
    exit 1
fi

# A lifetime parameter may be pinned to the caller's own frame: a caller local outlives any call
# that borrows it. The frame is not a region with an extent, so both sides check the same thing in
# its place — the actual is a place the caller holds outright.
set +e
run_json_report "$ROOT_DIR/examples/frame_lifetime.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; assert any(node["kind"] == "resource-call-region" and node["secondary_name"] == "@call-frame" for node in nodes)'
frame_lifetime_status=${PIPESTATUS[1]}
set -e
if [[ "$frame_lifetime_status" -ne 0 ]]; then
    printf 'proof test matrix failed: frame lifetime pinning\n' >&2
    exit 1
fi

# A moved binding is no longer a place the caller holds, and a lifetime no formal carries is pinned
# by nothing at all.
set +e
run_json_report "$ROOT_DIR/examples/rejected_frame_lifetime.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("resource-use-after-move", "lends_moved_local") in findings; assert ("region-call-opaque", "lends_moved_local") in findings; assert ("region-call-opaque", "unreceived_lifetime") in findings; assert not any(node["kind"] == "resource-call-region" and node["secondary_name"] == "@call-frame" for node in report["kernel"]["nodes"])'
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
run_json_report "$ROOT_DIR/examples/unnamed_lifetime_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; resource = {goal["name"]: goal["proven"] for goal in report["goals"] if goal["rule"] == "resource-safety"}; assert resource.get("lends_region_value") is True; assert resource.get("lends_region_value_exclusively") is True; kinds = {finding["kind"] for finding in report["findings"]}; assert "region-call-opaque" not in kinds; assert "borrow-call-opaque" not in kinds'
unnamed_lifetime_status=${PIPESTATUS[1]}
set -e
if [[ "$unnamed_lifetime_status" -ne 0 ]]; then
    printf 'proof test matrix failed: lending a region-owned actual to an unnamed lifetime\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_unnamed_lifetime_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("region-call-opaque", "lends_region_value_to_a_keeper") in findings'
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
run_json_report "$ROOT_DIR/examples/captured_block.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("obligations_after_the_loop_are_checked", "index-upper") in proven; assert ("obligations_inside_the_loop_are_checked", "index-upper") in proven; assert not report["findings"]'
captured_block_status=${PIPESTATUS[1]}
set -e
if [[ "$captured_block_status" -ne 0 ]]; then
    printf 'proof test matrix failed: captured block statements\n' >&2
    exit 1
fi

# The write-back is havocked, so nothing established before the loop survives it, and an
# unprovable obligation inside the body stays visible instead of vanishing with the path.
set +e
run_json_report "$ROOT_DIR/examples/rejected_captured_block.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("fact_must_not_survive", "goal")] is False; assert goals[("value_must_not_survive", "goal")] is False; assert goals[("obligation_inside_is_not_skipped", "index-upper")] is False'
rejected_captured_block_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_captured_block_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a captured block let outer state survive\n' >&2
    exit 1
fi

# The capture list is the block's whole reach, so a binding it does not name keeps both its
# symbolic value and its facts across the block; a binding it does name keeps neither.
set +e
run_json_report "$ROOT_DIR/examples/uncaptured_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("value_outside_the_capture_list_survives", "goal") in proven; assert ("fact_outside_the_capture_list_survives", "goal") in proven; assert not report["findings"]'
uncaptured_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$uncaptured_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an uncaptured binding did not survive a captured block\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_uncaptured_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("overwritten_binding_must_not_survive", "goal")] is False; assert goals[("zero_iteration_fact_must_not_escape", "goal")] is False'
rejected_uncaptured_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_uncaptured_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a captured binding survived its own captured block\n' >&2
    exit 1
fi

# The capture list is not a bound on what a block writes: the compiler accepts a block whose body
# assigns an outer binding the list omits. Every such binding must lose its value and its facts.
set +e
run_json_report "$ROOT_DIR/examples/rejected_uncaptured_block_write.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; written = ("assigned_without_being_captured", "assigned_under_a_branch", "written_through_a_reference", "assigned_in_a_nested_block", "fact_over_a_written_binding"); assert all((owner, "call-requires-unproven") in owners for owner in written); goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert all(goals[(owner, "goal")] is False for owner in written); assert {kind for _, kind in owners} == {"call-requires-unproven"}'
rejected_uncaptured_block_write_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_uncaptured_block_write_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a binding written outside a block capture list kept its state\n' >&2
    exit 1
fi

# A loop that only writes elements of the collection it walks keeps that collection's extent, so
# the binder's own range still bounds the indexed write. Any body that can resize it keeps nothing.
set +e
run_json_report "$ROOT_DIR/examples/loop_element_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert {finding["kind"] for finding in report["findings"]} == {"loop-invariant-missing"}; assert not [goal for goal in report["goals"] if not goal["proven"]]; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert all((owner, "index-upper") in proven for owner in ("fill_in_place", "fill_under_a_branch", "fill_with_a_while", "a_recorded_count_survives", "aliased_elsewhere_but_not_in_the_body"))'
loop_element_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_element_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an element write lost the collection extent\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_loop_element_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; resized = ("a_push_in_the_body", "a_call_that_may_push", "a_whole_assignment", "one_whole_write_among_many", "a_reference_taken", "aliased_elsewhere_and_a_call_here"); assert all((owner, "index-upper-unproven") in owners for owner in resized); assert not any(goal["proven"] and goal["rule"] == "index-upper" for goal in report["goals"])'
rejected_loop_element_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_element_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a body that can resize a collection kept its extent\n' >&2
    exit 1
fi

# A bound travels across an equality: the chain reads `b == c` as both non-strict steps. Every
# goal has to replay, which is what makes the kernel's own equality step load-bearing.
set +e
run_json_report "$ROOT_DIR/examples/comparison_chain_equality.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("paired_write", "index-upper") in proven; assert ("equality_reversed", "index-upper") in proven; assert ("non_strict_through_an_equality", "goal") in proven; assert ("copy_into_a_paired_collection", "index-upper") in proven'
comparison_chain_equality_status=${PIPESTATUS[1]}
set -e
if [[ "$comparison_chain_equality_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a bound did not travel across an equality, or did not replay\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_comparison_chain_equality.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = ("equality_alone_is_not_strict", "two_equalities_give_no_strict_goal", "inequality_is_not_a_step", "an_equality_to_the_wrong_term"); goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert all(goals[(owner, "goal")] is False for owner in refused); formation = [finding for finding in report["findings"] if finding["name"] == "struct_equality_is_not_an_order"]; assert len(formation) == 2 and all(finding["kind"] == "contract-proposition-type" for finding in formation); assert {finding["kind"] for finding in report["findings"]} == {"contract-proposition-type", "ensure-unproven"}'
rejected_comparison_chain_equality_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_comparison_chain_equality_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an equality was read as a strict or a user comparison\n' >&2
    exit 1
fi

# A region-polymorphic function may state a contract about the extent of its own parameter. Only
# the extent, and only when the declared type is a collection.
set +e
run_json_report "$ROOT_DIR/examples/region_extent_contract.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert all(reasons[owner] == "verified" for owner in ("bounded_without_indexing", "extent_in_an_ensure", "two_lifetimes", "indexes_under_its_own_precondition"))'
region_extent_contract_status=${PIPESTATUS[1]}
set -e
if [[ "$region_extent_contract_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a region-polymorphic function could not bound its own parameter\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_region_extent_contract.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(f["name"], f["kind"]) for f in report["findings"]}; refused = ("struct_count_is_not_an_extent", "an_element_in_a_contract", "a_field_of_an_element"); assert all((owner, "region-contract-unsupported") in owners for owner in refused); assert ("the_binding_itself", "contract-proposition-type") in owners; assert ("shared_cannot_be_returned_mutable", "region-return-witness-unsupported") in owners; assert {kind for _, kind in owners} == {"contract-proposition-type", "region-contract-unsupported", "region-return-witness-unsupported"}; goals = {(g["name"], g["rule"]): g["proven"] for g in report["goals"]}; assert goals[("shared_cannot_be_returned_mutable", "index-upper")] is True'
rejected_region_extent_contract_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_region_extent_contract_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a region-owned value entered a contract as if it were an extent\n' >&2
    exit 1
fi

# A statement that is just a call may name a region-owned binding; what it may not do is drop a
# result that carries a region.
set +e
run_json_report "$ROOT_DIR/examples/region_statement_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert all(reasons[owner] == "verified" for owner in ("pushes_into_a_region_collection", "pushes_through_a_region_struct", "pushes_without_a_lifetime"))'
region_statement_call_status=${PIPESTATUS[1]}
set -e
if [[ "$region_statement_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call statement on a region-owned receiver was refused\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_region_statement_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(f["name"], f["kind"]) for f in report["findings"]}; assert owners == {("discards_a_region_reference", "region-expression-unsupported")}'
rejected_region_statement_call_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_region_statement_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a discarded region reference was admitted\n' >&2
    exit 1
fi

# A helper that declares no lifetime may receive a region-owned reference: it cannot allocate into
# that region or return anything from it. A callee that returns a reference may not.
set +e
run_json_report "$ROOT_DIR/examples/region_lifetime_free_callee.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert all(reasons[owner] == "verified" for owner in ("region_caller", "caller_that_writes", "region_caller_of_pusher"))'
region_lifetime_free_callee_status=${PIPESTATUS[1]}
set -e
if [[ "$region_lifetime_free_callee_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a lifetime-free callee could not receive a region-owned reference\n' >&2
    exit 1
fi

# The pinned frontend also reports the overlapping actuals; the proof checker must refuse them on
# its own as well.
set +e
run_json_report "$ROOT_DIR/examples/rejected_region_lifetime_free_callee.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert [(diagnostic["line"], diagnostic["actual"]) for diagnostic in report["semantic_diagnostics"]] == [(22, "two_arguments")]; assert report["replay"]["gaps"] == 0; owners = {(f["name"], f["kind"]) for f in report["findings"]}; assert ("a_lifetime_free_callee_may_not_return_a_reference", "region-call-opaque") in owners; assert ("overlapping_mutable_actuals", "borrow-call-alias") in owners; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_lifetime_free_callee_may_not_return_a_reference"] != "verified"; assert reasons["overlapping_mutable_actuals"] != "verified"'
rejected_region_lifetime_free_callee_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_region_lifetime_free_callee_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a lend admitted a callee that keeps what it is lent\n' >&2
    exit 1
fi

# A short-circuit guard bounds the operand it guards, in the position that needs no statement.
set +e
run_json_report "$ROOT_DIR/examples/short_circuit_guard.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert all((owner, "index-upper") in proven for owner in ("guarded_and", "guarded_or", "guarded_if", "guarded_early_return", "guards_two_reads"))'
short_circuit_guard_status=${PIPESTATUS[1]}
set -e
if [[ "$short_circuit_guard_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a short-circuit guard did not bound the operand it guards\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_short_circuit_guard.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(f["name"], f["kind"]) for f in report["findings"]}; refused = ("off_by_one", "guards_another_name", "or_runs_when_the_guard_fails", "guard_comes_after", "guard_has_a_call"); assert all((owner, "index-upper-unproven") in owners for owner in refused); assert {kind for _, kind in owners} == {"index-upper-unproven"}; assert not any(g["proven"] and g["rule"] == "index-upper" for g in report["goals"])'
rejected_short_circuit_guard_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_short_circuit_guard_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a guard bounded something it does not guard\n' >&2
    exit 1
fi

# A pure callee's disjunctive postcondition survives the guard that uses it: an element write
# after `raise ... if not live(t, s)` keeps `s < CAPACITY` by unit resolution, and a
# short-circuit operand sees the guard call's summary. Inverted or conditional guards do not.
set +e
run_json_report "$ROOT_DIR/examples/call_guard_summaries.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert {("write_after_guard", "index-upper"), ("and_guard", "index-upper"), ("or_guard", "index-upper")} <= proven; origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}; assert "unit-resolution" in origins'
call_guard_summaries_status=${PIPESTATUS[1]}
set -e
if [[ "$call_guard_summaries_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a pure call guard did not carry its summary to the access it guards\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_call_guard_summaries.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("write_after_inverted_guard", "index-upper-unproven"), ("conditional_guard_call", "index-upper-unproven"), ("inverted_or_guard", "index-upper-unproven")} <= owners; assert not any(origin["kind"] == "unit-resolution" for goal in report["goals"] for origin in goal["fact_origins"] if origin)'
rejected_call_guard_summaries_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_call_guard_summaries_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call guard bounded an access on a path where it did not certify the slot\n' >&2
    exit 1
fi

# A range-loop binder's bound reaches a callee's `requires` from every call position: the
# binder's versioned value is resolved once, not twice. An unbounded range or successor does not.
set +e
run_json_report "$ROOT_DIR/examples/loop_binder_call_requires.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
loop_binder_call_requires_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_binder_call_requires_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a range-loop binder did not establish a callee precondition\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_loop_binder_call_requires.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("one_past", "call-requires-unproven"), ("successor", "call-requires-unproven")} <= owners'
rejected_loop_binder_call_requires_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_binder_call_requires_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a callee precondition was established for an unbounded slot\n' >&2
    exit 1
fi

# `x != c` at an interval endpoint narrows the interval by one: unsigned `length != 0` gives
# `length >= 1`. A disequality away from an endpoint narrows nothing.
set +e
run_json_report "$ROOT_DIR/examples/disequality_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
disequality_bounds_status=${PIPESTATUS[1]}
set -e
if [[ "$disequality_bounds_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an endpoint disequality did not narrow an unsigned interval\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_disequality_bounds.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("interior", "ensure-unproven"), ("not_endpoint", "ensure-unproven")} <= owners'
rejected_disequality_bounds_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_disequality_bounds_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a disequality away from an interval endpoint narrowed the interval\n' >&2
    exit 1
fi

# `x == if c then a else b` splits into the arm cases, each with its condition or its negation.
set +e
run_json_report "$ROOT_DIR/examples/conditional_equality_split.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
conditional_equality_split_status=${PIPESTATUS[1]}
set -e
if [[ "$conditional_equality_split_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an equality with a conditional value was not split into its arms\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_conditional_equality_split.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("clamp_off_by_one", "ensure-unproven")} <= owners'
rejected_conditional_equality_split_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_conditional_equality_split_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a conditional equality proved a bound neither arm gives\n' >&2
    exit 1
fi

# A local bound to a place (`last: T = xs[i]`) carries its facts to that place and back.
set +e
run_json_report "$ROOT_DIR/examples/place_aliases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
place_aliases_status=${PIPESTATUS[1]}
set -e
if [[ "$place_aliases_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a place read through its local alias did not keep the facts of its alias\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_place_aliases.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("other_element", "ensure-unproven")} <= owners'
rejected_place_aliases_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_place_aliases_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an alias transferred facts to a different place\n' >&2
    exit 1
fi

# A bound chained through a field place or a loop binder (`at < t.length <= CAP`) closes
# once the place is generalized to a fresh name.
set +e
run_json_report "$ROOT_DIR/examples/guarded_differences.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("last_of_four", "goal") in proven; assert ("strict_chain_sum", "goal") in proven; assert ("fourth_byte", "index-upper") in proven'
guarded_differences_status=${PIPESTATUS[1]}
set -e
if [[ "$guarded_differences_status" -ne 0 ]]; then
  printf 'proof test matrix failed: a guarded difference or plain order did not bound a goal sum\n' >&2
  exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_guarded_differences.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("modular_sum_fact", "ensure-unproven"), ("modular_sum_bound", "index-upper-unproven"), ("unguarded_difference", "ensure-unproven"), ("one_past_the_span", "ensure-unproven"), ("one_past_in_text", "index-upper-unproven")}'
rejected_guarded_differences_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_guarded_differences_status" -ne 0 ]]; then
  printf 'proof test matrix failed: a modular sum or unguarded difference bounded a goal\n' >&2
  exit 1
fi
printf 'guarded differences: exact differences and plain orders bound goal sums; modular and unguarded forms refused\n'
set +e
run_json_report "$ROOT_DIR/examples/literal_widths.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; proven = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] == "goal"}; assert proven == {"unsigned_maximum", "signed_minimum", "signed_step_down", "exact_difference", "small_shift"}'
literal_widths_status=${PIPESTATUS[1]}
set -e
if [[ "$literal_widths_status" -ne 0 ]]; then
  printf 'proof test matrix failed: a literal that fits its width was refused\n' >&2
  exit 1
fi
set +e
run_json_report "$ROOT_DIR/examples/rejected_literal_widths.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("plus_zero", "ensure-unproven"), ("times_one", "ensure-unproven"), ("wide_difference", "ensure-unproven"), ("wide_sum", "ensure-unproven"), ("negative_unsigned", "ensure-unproven"), ("wide_signed", "ensure-unproven"), ("below_signed_minimum", "ensure-unproven"), ("wide_goal", "ensure-unproven")}'
rejected_literal_widths_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_literal_widths_status" -ne 0 ]]; then
  printf 'proof test matrix failed: a literal wrapped by its width was read exactly\n' >&2
  exit 1
fi
printf 'literal widths: literals that fit their width prove; wrapped literals prove nothing\n'
set +e
run_json_report "$ROOT_DIR/examples/field_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
field_places_status=${PIPESTATUS[1]}
set -e
if [[ "$field_places_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a bound chained through a field place did not close\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_field_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("non_strict", "index-upper-unproven"), ("other_field", "index-upper-unproven"), ("other_record", "index-upper-unproven")} <= owners'
rejected_field_places_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_field_places_status" -ne 0 ]]; then
    printf 'proof test matrix failed: field generalization linked unrelated places\n' >&2
    exit 1
fi

# A shared borrow lent inside a loop keeps its field facts when the frame received no mutable
# path; a mutable parameter, a reference field or a mutable global withdraws the rule.
set +e
run_json_report "$ROOT_DIR/examples/shared_fixed_borrows.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
shared_fixed_borrows_status=${PIPESTATUS[1]}
set -e
if [[ "$shared_fixed_borrows_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a closed frame lost a field fact of a shared borrow across a call\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_shared_fixed_borrows.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("with_a_mutable_parameter", "call-requires-unproven"), ("with_a_reference_field", "call-requires-unproven")}'
rejected_shared_fixed_borrows_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_shared_fixed_borrows_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a frame holding a mutable path kept a field fact across a call\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_shared_fixed_global.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("scan", "call-requires-unproven")}'
rejected_shared_fixed_global_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_shared_fixed_global_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a mutable global left a field fact fixed across a call\n' >&2
    exit 1
fi

# A scalar bound to a call result carries the call summary over the bound name.
set +e
run_json_report "$ROOT_DIR/examples/bound_call_summaries.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
bound_call_summaries_status=${PIPESTATUS[1]}
set -e
if [[ "$bound_call_summaries_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call summary did not carry over the name bound to the call\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_bound_call_summaries.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("stronger_than_the_summary", "ensure-unproven"), ("unproven_precondition", "call-requires-unproven"), ("unproven_precondition", "ensure-unproven")}'
rejected_bound_call_summaries_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_bound_call_summaries_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a bound call result proved more than its summary\n' >&2
    exit 1
fi

# A pure call over a by-value payload-enum binding keeps its summary across the next call.
set +e
run_json_report "$ROOT_DIR/examples/value_call_arguments.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
value_call_arguments_status=${PIPESTATUS[1]}
set -e
if [[ "$value_call_arguments_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call over a payload-enum value lost its summary at the next call\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_value_call_arguments.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("container", "ensure-unproven"), ("view", "ensure-unproven"), ("hierarchy", "ensure-unproven"), ("common_fields", "ensure-unproven"), ("lent", "ensure-unproven")}'
rejected_value_call_arguments_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_value_call_arguments_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call over an enum a second path reaches kept its summary\n' >&2
    exit 1
fi

# A witnessed pure call result is generalized like a field place and keeps its declared width.
set +e
run_json_report "$ROOT_DIR/examples/call_result_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
call_result_places_status=${PIPESTATUS[1]}
set -e
if [[ "$call_result_places_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a bounded pure call result was not generalized\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_call_result_places.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("wraps", "ensure-unproven"), ("other_argument", "ensure-unproven"), ("stale_argument", "ensure-unproven")}'
rejected_call_result_places_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_call_result_places_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call result was bounded or identified too loosely\n' >&2
    exit 1
fi

# A join decides a fact over each arm value when an arm rebound a name over itself.
set +e
run_json_report "$ROOT_DIR/examples/rebind_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
rebind_join_status=${PIPESTATUS[1]}
set -e
if [[ "$rebind_join_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a guarded self-increment lost the invariant at the join\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_rebind_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("overshoot", "ensure-unproven"), ("overshoot", "invariant-not-preserved")}'
rejected_rebind_join_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_rebind_join_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a join kept a fact an arm value does not satisfy\n' >&2
    exit 1
fi

# An integer conversion may sit in an if-expression arm that does not always run.
set +e
run_json_report "$ROOT_DIR/examples/conditional_conversions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
conditional_conversions_status=${PIPESTATUS[1]}
set -e
if [[ "$conditional_conversions_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a conversion in a conditional arm was refused\n' >&2
    exit 1
fi
