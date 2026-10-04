# shellcheck shell=bash
# Signedness, fixed-width arithmetic and source-literal soundness regressions.
# The sign of a product is decidable from its operands' signs. The producer and the replay kernel
# state the rule identically, so every one of these must also replay: a tier only the producer had
# would show up as a gap, not a proof.
set +e
run_json_report "$ROOT_DIR/examples/product_sign.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"nonnegative_product", "negative_operands", "mixed_operands", "strict_product", "strict_negative", "mirrored_forms"} <= names'
product_sign_status=${PIPESTATUS[1]}
set -e
if [[ "$product_sign_status" -ne 0 ]]; then
    printf 'proof test matrix failed: product sign reasoning\n' >&2
    exit 1
fi

# A strict conclusion needs strict premises, a mixed pair is not nonnegative, one known sign is not
# two, a bound other than zero is not a sign, and sign facts about other terms say nothing here.
set +e
run_json_report "$ROOT_DIR/examples/rejected_product_sign.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert not any(goal["proven"] and goal["rule"] != "resource-safety" for goal in report["goals"]); refused = {finding["name"] for finding in report["findings"] if finding["kind"] == "ensure-unproven"}; assert {"strict_from_nonstrict", "mixed_claimed_nonnegative", "one_operand_known", "nonzero_bound", "signs_of_other_terms", "signed_square_can_overflow_negative"} <= refused'
rejected_product_sign_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_product_sign_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unsound product sign was concluded\n' >&2
    exit 1
fi

# A full-width unsigned literal is stored in the signed AST integer slot as its bit pattern. It
# must not contradict the unsigned lower bound and make the bounded model vacuously prove a false
# conclusion; ordinary unsigned reflexivity should remain provable.
set +e
run_json_report "$ROOT_DIR/examples/rejected_u64_max_conflict.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed" and report["verification_state"] == "disproved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}; assert not functions["u64_max_does_not_imply_zero"]["verified"]; assert not functions["usize_max_does_not_imply_zero"]["verified"]; assert functions["u64_reflexive_equality_remains_provable"]["verified"]; assert not functions["u64_max_is_not_less_than_zero"]["verified"]; assert not functions["usize_global_max_is_not_negative"]["verified"]; assert not functions["usize_local_max_is_not_negative"]["verified"]; assert not functions["u8_overflow_is_not_unequal"]["verified"]; assert not functions["u8_shift_outside_width_is_not_zero"]["verified"]; assert not functions["u8_overflow_hidden_in_conditional_is_not_nonzero"]["verified"]; refused = {f["name"]: f for f in report["findings"] if f["kind"] == "ensure-unproven"}; disproved = {name for name, finding in refused.items() if finding["status"] == "disproved" and finding["counterexample_found"]}; assert disproved == {"u64_max_does_not_imply_zero", "u64_max_is_not_less_than_zero"}; unknown = {name for name, finding in refused.items() if finding["status"] == "unknown" and not finding["counterexample_found"]}; assert unknown == {"usize_max_does_not_imply_zero", "usize_global_max_is_not_negative", "usize_local_max_is_not_negative", "u8_overflow_is_not_unequal", "u8_shift_outside_width_is_not_zero", "u8_overflow_hidden_in_conditional_is_not_nonzero"}'
rejected_u64_max_conflict_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_u64_max_conflict_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a reinterpreted u64 maximum created a vacuous proof\n' >&2
    exit 1
fi

# The i64-backed arena must neither decide a negative u64 bit pattern using signed order nor
# fold fixed-width unsigned arithmetic as unbounded signed arithmetic. Exercise both exact and
# simp tactic replay against their false claims; either accepting one would be a kernel soundness
# failure even if ordinary source analysis correctly reports the goal as unknown.
readonly REJECTED_U64_MAX_GOAL_ID=7
readonly REJECTED_U64_MAX_GOAL_FINGERPRINT=3959704679
readonly REJECTED_U8_OVERFLOW_GOAL_ID=13
readonly REJECTED_U8_OVERFLOW_GOAL_FINGERPRINT=3492578551
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

# A `u64` literal above the i64 range keeps its fixed width through proof search and replay.
# `usize` remains open until a target-width sort is represented in the kernel; neither case may
# be decided from a wrapped signed payload, and refusals do not claim counterexamples.
set +e
run_json_report "$ROOT_DIR/examples/typed_unsigned_literals.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed" and report["verification_state"] == "disproved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0 and report["replay"]["certificates"] == report["replay"]["replayed"]; assert all(not goal["proven"] or goal["replay_status"] == "replayed" for goal in report["goals"]); assert report["summary"]["proven"] + report["summary"]["unproven"] == report["summary"]["obligations"]; functions = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}; proved = {"u64_max_exceeds_zero", "u64_max_equals_itself", "u64_max_exceeds_high_bit"}; refused = {"usize_high_bit_at_least_small", "u64_max_is_not_below_zero", "u64_high_bit_is_not_below_max", "u64_max_is_not_zero", "untyped_wrapped_literal_is_not_ordered"}; assert all(functions[name]["verified"] for name in proved); assert not any(functions[name]["verified"] for name in refused); findings = {f["name"]: f for f in report["findings"] if f["kind"] == "ensure-unproven"}; assert set(findings) == refused; disproved = {name for name, finding in findings.items() if finding["status"] == "disproved" and finding["counterexample_found"]}; assert disproved == {"u64_max_is_not_below_zero", "u64_high_bit_is_not_below_max", "u64_max_is_not_zero"}; unknown = {name for name, finding in findings.items() if finding["status"] == "unknown" and not finding["counterexample_found"]}; assert unknown == {"usize_high_bit_at_least_small", "untyped_wrapped_literal_is_not_ordered"}; function_status = {item["name"]: item for item in report["functions"]}; assert not function_status["usize_high_bit_at_least_small"]["proved"] and function_status["usize_high_bit_at_least_small"]["open_goals"] > 0; usize_goal = next(goal for goal in report["goals"] if goal["name"] == "usize_high_bit_at_least_small" and goal["rule"] == "goal"); assert not usize_goal["proven"] and usize_goal["refusal_gate"] == "ambiguous-constant-goal"'
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
