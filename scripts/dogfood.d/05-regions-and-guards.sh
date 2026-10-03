# shellcheck shell=bash
# Part 5 of scripts/dogfood.sh; sourced in order by it, never run alone.
python3 - "$REPORT_DIR/sum_bound.json" "$REPORT_DIR/rejected_sum_bound.json" <<'PY'
import json
import sys

bounded, wrapped = sys.argv[1:]
with open(bounded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: sum bound fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a sum-bound certificate was left unreplayed")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for owner in ("transpose_the_subtraction", "a_term_under_the_bound", "the_same_for_a_signed_sum", "commuted"):
    if (owner, "goal") not in proven:
        raise SystemExit("dogfood failed: %s did not bound its sum" % owner)
with open(wrapped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: sum bound boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("a_modular_premise_is_not_a_bound", "the_subtraction_needs_its_guard", "a_non_strict_step_gives_no_strict_goal", "a_bound_on_another_term"):
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s bounded a sum nothing bounds" % owner)
print("dogfood sum_bound: a guarded subtraction bounds a sum, a wrapped premise does not")
PY

# `or` and `and` short-circuit: an operand the left one settles owes no range argument, and a
# left operand that settles nothing still owes the right one its own.
python3 - "$REPORT_DIR/settled_operand.json" "$REPORT_DIR/rejected_settled_operand.json" <<'PY'
import json
import sys

settled, live = sys.argv[1:]
with open(settled, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: settled operand fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a settled-operand certificate was left unreplayed")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for owner in ("empty_range_is_valid", "a_settled_conjunct", "the_live_operand_is_still_owed"):
    if (owner, "goal") not in proven:
        raise SystemExit("dogfood failed: %s was charged for an unreachable operand" % owner)
with open(live, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: settled operand boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("or_left_false_still_owes_the_right", "and_left_true_still_owes_the_right", "a_settled_operand_does_not_settle_a_sibling", "an_unsettled_left_keeps_the_gate"):
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s let a neighbour settle a live operand" % owner)
print("dogfood settled_operand: a settled operand is free, a live one still owes its range")
PY

# An early return leaves its condition negated. That negation is an order between the same two
# atoms, and it says nothing about another pair, another direction, or a strict bound.
python3 - "$REPORT_DIR/negated_guard_order.json" "$REPORT_DIR/rejected_negated_guard_order.json" <<'PY'
import json
import sys

reaching, silent = sys.argv[1:]
with open(reaching, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: negated guard fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a negated-guard certificate was left unreplayed")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for owner in ("a_guard_reaches_past_its_own_return", "a_guard_inside_a_disjunction_still_reaches", "a_bounded_sum_follows_from_the_pair"):
    if (owner, "goal") not in proven:
        raise SystemExit("dogfood failed: %s did not reach past its own return" % owner)
with open(silent, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: negated guard boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("a_negation_of_the_wrong_order", "an_inequality_is_not_an_order", "a_guard_on_another_pair", "the_bound_the_guards_give_is_not_strict"):
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s read more out of a negated guard than it says" % owner)
print("dogfood negated_guard_order: a negated guard is an order, and only over the pair it names")
PY

# A place order guards its own subtraction, a conjunction is read as its conjuncts, a negation
# closes the branch it refutes, and a non-wrapping unsigned value is nonnegative -- each saying
# only what it says.
python3 - "$REPORT_DIR/place_order.json" "$REPORT_DIR/rejected_place_order.json" <<'PY'
import json
import sys

readable, literal = sys.argv[1:]
with open(readable, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: place order fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a place-order certificate was left unreplayed")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_place_guards_its_own_subtraction", "a_conjunction_is_read_as_its_conjuncts", "a_denied_disjunct_leaves_the_other", "a_guarded_difference_is_nonnegative", "a_summary_the_caller_guarded_on"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s could not read a fact its list states" % owner)
with open(literal, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: place order boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_place_order_in_the_wrong_direction", "a_place_order_on_another_pair", "a_disjunct_is_not_a_conjunct", "a_negation_denies_only_itself", "nonnegative_is_not_positive", "an_unguarded_summary_asserts_nothing"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s read a fact list for more than it states" % owner)
print("dogfood place_order: a place order guards its own subtraction, and says nothing further")
PY

# An unsigned machine value is nonnegative whatever it holds. The marker is over the place, it
# answers only that one question, and an ambiguous qualified leaf names no struct at all.
python3 - "$REPORT_DIR/unsigned_place.json" "$REPORT_DIR/rejected_unsigned_place.json" <<'PY'
import json
import sys

typed, untyped = sys.argv[1:]
with open(typed, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: unsigned place fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: an unsigned-place certificate was left unreplayed")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_guarded_range_over_a_field", "a_field_is_nonnegative", "an_unguarded_difference_is_still_nonnegative", "a_qualified_struct_field_is_nonnegative"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s did not know its field was unsigned" % owner)
with open(untyped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: unsigned place boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_signed_field_is_not_nonnegative", "a_field_is_not_positive", "a_call_result_carries_no_marker", "an_unsigned_field_has_no_upper_bound", "an_ambiguous_leaf_names_no_struct"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s read a place marker for more than it says" % owner)
print("dogfood unsigned_place: an unsigned field is nonnegative, and the marker says nothing more")
PY

# An empty literal is empty, and that is the whole of what the literal says: not a length after a
# push, not a length for a parameter, and not a bound on any element.
python3 - "$REPORT_DIR/literal_extent.json" "$REPORT_DIR/rejected_literal_extent.json" <<'PY'
import json
import sys

literal, absent = sys.argv[1:]
with open(literal, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: literal extent fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a literal-extent certificate was left unreplayed")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("an_empty_literal_is_empty", "a_length_invariant_starts_at_zero"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s did not know its literal was empty" % owner)
with open(absent, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: literal extent boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_push_is_not_modelled", "a_parameter_has_no_literal", "a_field_named_count_is_not_a_length", "a_literal_length_is_not_an_element_bound", "a_non_empty_literal_length_is_not_read", "a_short_literal_has_its_own_length_only"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s read a length where no literal states one" % owner)
print("dogfood literal_extent: an empty literal is empty, and says nothing past that")
PY

# A collection a local owns outright is a binding no callee can name, so its extent survives a
# call; a lent one, a reference, and the receiver of a builtin do not.
python3 - "$REPORT_DIR/owned_extent.json" "$REPORT_DIR/rejected_owned_extent.json" <<'PY'
import json
import sys

owned, reachable = sys.argv[1:]
with open(owned, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: owned extent fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: an owned-extent certificate was left unreplayed")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("an_owned_extent_survives_a_call_that_cannot_reach_it", "an_owned_extent_survives_another_collection_being_grown"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost an extent no callee can reach" % owner)
with open(reachable, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: owned extent boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_lent_local_loses_its_extent", "a_reference_local_owns_nothing", "a_push_gives_no_new_length", "a_shared_argument_still_loses_the_extent"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s kept an extent a callee can reach" % owner)
print("dogfood owned_extent: an owned extent survives, a reachable one does not")
PY

# A capture list bounds nothing and evidences nothing: a capture the body only reads keeps its
# facts, and a binding the body assigns or hands to a writer does not.
python3 - "$REPORT_DIR/captured_scalar.json" "$REPORT_DIR/rejected_captured_scalar.json" <<'PY'
import json
import sys

read_only, written = sys.argv[1:]
with open(read_only, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: captured scalar fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a captured-scalar certificate was left unreplayed")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_read_only_capture_keeps_its_precondition", "a_read_only_capture_survives_a_mutating_body"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost a fact its captured body never touched" % owner)
with open(written, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: captured scalar boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_capture_the_body_assigns_is_forgotten", "a_capture_handed_to_a_writer_is_forgotten", "an_uncaptured_binding_the_body_assigns_is_forgotten"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s kept a fact its captured body falsified" % owner)
print("dogfood captured_scalar: a read-only capture keeps its facts, a written binding does not")
PY

# A statement the checker cannot read is refused and havocs what follows it; a `pass` arm, and a
# match whose arms agree, keep the state before it.
python3 - "$REPORT_DIR/no_op_statement.json" "$REPORT_DIR/rejected_no_op_statement.json" <<'PY'
import json
import sys

readable, unreadable = sys.argv[1:]
with open(readable, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: no-op statement fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_condition_keeps_the_state", "every_arm_returning_keeps_it_too", "a_pass_arm_keeps_the_state"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost the state before a match" % owner)
with open(unreadable, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: no-op boundary fixture did not fail cleanly")
# The refusal is reported as unsupported. The fixture's second function then shows that it
# reaches past the match: the precondition is gone at the later call, which is reported too.
kinds = {(f["name"], f["kind"]) for f in report["findings"]}
if ("a_dropped_arm_is_refused", "expression-unsupported") not in kinds or ("the_refusal_reaches_past_the_match", "expression-unsupported") not in kinds:
    raise SystemExit("dogfood failed: an unreadable statement was not reported as unsupported")
if not kinds <= {("a_dropped_arm_is_refused", "expression-unsupported"), ("the_refusal_reaches_past_the_match", "expression-unsupported"), ("the_refusal_reaches_past_the_match", "call-requires-unproven")}:
    raise SystemExit("dogfood failed: an unreadable statement produced an unexpected finding: %s" % sorted(kinds))
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_dropped_arm_is_refused", "the_refusal_reaches_past_the_match"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s admitted a statement the checker cannot read" % owner)
print("dogfood no_op_statement: an unreadable statement is refused, and `pass` or a plain condition is not")
PY

# A call is modelled at a statement boundary; buried in a larger value it has none and is refused.
python3 - "$REPORT_DIR/nested_call_value.json" "$REPORT_DIR/rejected_nested_call_value.json" <<'PY'
import json
import sys

bound, buried = sys.argv[1:]
with open(bound, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: nested call fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_call_bound_first_is_modelled", "the_binding_keeps_the_state_after_it", "a_call_bound_before_a_conditional_is_modelled"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s did not model a call bound to a local" % owner)
with open(buried, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: nested call boundary fixture did not fail cleanly")
if {f["kind"] for f in report["findings"]} != {"expression-unsupported"}:
    raise SystemExit("dogfood failed: a call with no statement boundary was not reported")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_call_nested_in_a_tuple_is_refused", "the_refusal_reaches_past_the_statement", "a_call_inside_a_conditional_is_refused"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s admitted a call it cannot model" % owner)
print("dogfood nested_call_value: a call needs a statement boundary, and a binding gives it one")
PY

# A collection builtin writes its receiver, so the borrow rules apply to it; a region argument
# withdraws the admission rather than guessing a lifetime.
python3 - "$REPORT_DIR/collection_builtin.json" "$REPORT_DIR/rejected_collection_builtin.json" <<'PY'
import json
import sys

modelled, withdrawn = sys.argv[1:]
with open(modelled, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: collection builtin fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_push_is_a_write_to_its_receiver", "a_copy_clears_and_extends", "a_borrow_taken_after_the_write_is_fine", "a_truncate_is_a_write", "a_conversion_has_no_receiver_to_write"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s did not model a collection builtin" % owner)
with open(withdrawn, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: collection builtin boundary fixture did not fail cleanly")
# Stage0 describes this as a builtin `push` error; the pinned self-hosted frontend reports the
# same safety fact as a region-escape diagnostic. Assert the invariant rather than a frontend
# wording: exactly one hard error, naming the local arena and the longer-lived destination.
if report["summary"]["semantic_errors"] != 1 or not any(
    diagnostic["actual"] == "scratch"
    and "longer-lived region" in diagnostic["message"]
    for diagnostic in report["semantic_diagnostics"]
):
    raise SystemExit("dogfood failed: unsafe nested-region growth was not diagnosed by the compiler")
if {f["kind"] for f in report["findings"]} != {"borrow-write-conflict", "borrow-call-opaque"}:
    raise SystemExit("dogfood failed: a builtin write escaped the borrow rules")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_push_while_a_borrow_is_live", "a_region_argument_withdraws_the_admission", "an_unmodelled_builtin_is_refused"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s admitted a builtin call it does not model" % owner)
print("dogfood collection_builtin: a builtin writes its receiver, and the borrow rules see it")
PY

python3 - "$REPORT_DIR/rejected_shadowed_collection_builtin.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
assert any(
    finding["kind"] == "borrow-call-opaque"
    and finding["name"] == "shadowed_push_must_not_be_verified"
    for finding in report["findings"]
)
reasons = {
    declaration["name"]: declaration["verification_reason"]
    for declaration in report["declaration_details"]
    if declaration["kind"] == "function"
}
assert reasons["shadowed_push_must_not_be_verified"] == "body-unverified"
print("dogfood rejected_shadowed_collection_builtin: declared method names cannot use builtin effects")
PY

# A call in a loop condition is opaque, and an opaque condition leaves the loop with no post-state
# claim; the same loop over a bound limit keeps its condition.
python3 - "$REPORT_DIR/bound_loop_condition.json" "$REPORT_DIR/rejected_bound_loop_condition.json" <<'PY'
import json
import sys

bound, opaque = sys.argv[1:]
with open(bound, encoding="utf-8") as handle:
    report = json.load(handle)
if report["replay"]["gaps"] or report["summary"]["semantic_errors"]:
    raise SystemExit("dogfood failed: bound loop condition fixture did not run cleanly")
if {f["kind"] for f in report["findings"]} != {"loop-invariant-missing"}:
    raise SystemExit("dogfood failed: a bound loop condition was still reported opaque")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
if reasons.get("a_bound_limit_leaves_the_condition_readable") != "contract-verified-widened-state":
    raise SystemExit("dogfood failed: a bound loop condition lost its post-state claim")
with open(opaque, encoding="utf-8") as handle:
    report = json.load(handle)
if report["replay"]["gaps"] or report["summary"]["semantic_errors"]:
    raise SystemExit("dogfood failed: opaque loop condition fixture did not run cleanly")
if {f["kind"] for f in report["findings"]} != {"loop-condition-opaque", "loop-invariant-missing"}:
    raise SystemExit("dogfood failed: a call in a loop condition was read as a condition")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
if reasons.get("a_call_in_the_condition_is_opaque") != "body-unverified":
    raise SystemExit("dogfood failed: an opaque loop condition was admitted")
print("dogfood bound_loop_condition: a bound limit keeps the condition, a call in one does not")
PY

# A block statement discards its own value and nothing else; a collection's length is a scalar copy.
python3 - "$REPORT_DIR/block_statement_region.json" "$REPORT_DIR/rejected_block_statement_region.json" <<'PY'
import json
import sys

allowed, refused = sys.argv[1:]
with open(allowed, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: block statement fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a block-statement certificate was left unreplayed")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_captured_loop_over_a_region_binding", "an_extent_argument_is_a_scalar"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s was read as discarding a region value" % owner)
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: discarded region fixture did not fail cleanly")
if {f["kind"] for f in report["findings"]} != {"region-expression-unsupported"}:
    raise SystemExit("dogfood failed: a discarded region value was not reported")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_discarded_region_value_is_refused", "parentheses_do_not_hide_it"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s admitted a discarded region value" % owner)
print("dogfood block_statement_region: a block discards its own value, and a length is a scalar")
PY

# A loop invariant cannot appear in a compiled source here, so a loop needing one for its index
# bound is written not to need it.
python3 - "$REPORT_DIR/forward_scan.json" "$REPORT_DIR/rejected_forward_scan.json" <<'PY'
import json
import sys

forward, downward = sys.argv[1:]
with open(forward, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: forward scan fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_forward_scan_keeps_the_last_match", "an_existence_check_does_not_depend_on_order"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s did not carry its own index bound" % owner)
with open(downward, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: downward scan fixture did not fail cleanly")
if {f["kind"] for f in report["findings"]} != {"index-upper-unproven", "loop-invariant-missing"}:
    raise SystemExit("dogfood failed: a downward scan was given a bound it never states")
print("dogfood forward_scan: a forward scan carries its bound, a downward one needs an invariant")
PY

# A root the body writes only elements under keeps every count under it; a whole field write keeps
# none, including the count the loop is iterating.
python3 - "$REPORT_DIR/nested_extent.json" "$REPORT_DIR/rejected_nested_extent.json" <<'PY'
import json
import sys

kept, lost = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: nested extent fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_loop_over_one_field_writing_another", "the_guard_may_come_first"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost a nested extent to an element write beside it" % owner)
with open(lost, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: nested extent boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
if reasons.get("a_whole_field_write_loses_every_extent") != "body-unverified":
    raise SystemExit("dogfood failed: a whole field write kept an extent under its root")
print("dogfood nested_extent: an element write keeps every count under the root, a whole write none")
PY

# A binding that holds its value is this frame's storage, so a callee cannot reach its fields; a
# binding that holds a reference does not own what it names.
python3 - "$REPORT_DIR/value_root_field.json" "$REPORT_DIR/rejected_value_root_field.json" <<'PY'
import json
import sys

owned, referenced = sys.argv[1:]
with open(owned, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: value root fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_field_of_a_value_parameter_survives_a_call", "a_second_field_survives_it_too"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost a field of a binding it owns" % owner)
with open(referenced, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: value root boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_field_of_a_mutable_reference_does_not_survive", "a_field_of_a_shared_reference_does_not_either"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s kept a field of a reference across a call" % owner)
print("dogfood value_root_field: a field of an owned binding survives a call, a reference's does not")
PY

# A shared borrow cannot be resized for the borrow's lifetime, so a loop keeps the guard taken
# over its count. A mutable borrow and a rewritten scalar argument must still lose it.
python3 - "$REPORT_DIR/shared_extent_loop.json" "$REPORT_DIR/rejected_shared_extent_loop.json" <<'PY'
import json
import sys

kept, moved = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: shared extent fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_shared_borrow_keeps_its_extent", "a_later_lend_does_not_reach_backwards", "a_lend_inside_the_loop"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost a shared borrow's extent at loop entry" % owner)
with open(moved, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: shared extent boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_mutable_borrow_loses_its_extent", "a_lent_mutable_borrow_loses_it_too", "a_rewritten_argument_loses_the_guard"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s kept a guard over a quantity the loop can move" % owner)
print("dogfood shared_extent_loop: a shared borrow keeps its extent through a loop, a mutable one does not")
PY

# A fact over a collection literal has to find its own trace, or the certificate carrying it gaps.
python3 - "$REPORT_DIR/replay_literal_facts.json" "$REPORT_DIR/rejected_replay_literal_facts.json" <<'PY'
import json
import sys

carried, refused = sys.argv[1:]
with open(carried, encoding="utf-8") as handle:
    report = json.load(handle)
if report["replay"]["gaps"] or report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a fact over a collection literal did not replay")
lower = [g for g in report["goals"] if g["rule"] == "index-lower"]
if len(lower) != 5 or not all(g["proven"] and g["replay_status"] == "replayed" for g in lower):
    raise SystemExit("dogfood failed: a lower bound over a literal-bound local was lost")
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: literal boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_rebound_literal_loses_its_guard", "a_guard_for_one_literal_is_not_a_guard_for_another", "an_empty_literal_has_no_element"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s borrowed a guard recorded for another literal" % owner)
print("dogfood replay_literal_facts: a fact over a collection literal replays, and only against its own literal")
PY

# Every unsigned result is nonnegative even if it wraps; other integer-bound claims still need a
# wrap proof. A width marker must not be inherited from a signed call result or branch condition.
python3 - "$REPORT_DIR/unsigned_nonnegative_sum.json" "$REPORT_DIR/rejected_unsigned_nonnegative_sum.json" <<'PY'
import json
import sys

held, refused = sys.argv[1:]
with open(held, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: nonnegativity fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_sum_is_never_negative", "a_product_is_never_negative", "a_guarded_sum_is_nonnegative", "a_field_and_a_binder", "a_place_width_survives_a_call"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost a nonnegativity claim to the wrap guard" % owner)
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: nonnegativity boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("an_unguarded_difference_is_nonnegative", "a_nested_difference_is_nonnegative"):
    if reasons.get(owner) != "verified":
        raise SystemExit("dogfood failed: unsigned result nonnegativity was lost for %s" % owner)
if reasons.get("an_exact_guard_bounds_its_own_sum") != "verified":
    raise SystemExit("dogfood failed: an exact guard no longer bounds its own sum")
for owner in ("a_signed_sum_may_be_negative", "a_strict_claim_is_not_admitted", "a_wrapping_sum_bounds_nothing", "a_wrapping_sum_is_no_index"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s was admitted by the nonnegativity rule" % owner)
print("dogfood unsigned_nonnegative_sum: an unsigned sum is nonnegative without a wrap proof, and bounds nothing")
PY

# A negated guard is an order, and its complement is all it is.
python3 - "$REPORT_DIR/negated_guard_range.json" "$REPORT_DIR/rejected_negated_guard_range.json" <<'PY'
import json
import sys

read, refused = sys.argv[1:]
with open(read, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: negated guard fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_negated_range_check", "the_same_check_as_a_condition", "two_places", "a_modular_guard_bounds_its_own_sum"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s could not read its own guard" % owner)
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: negated guard boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_negated_struct_order_does_not_chain", "a_negated_struct_order_gives_no_strict_chain", "a_negated_modular_guard_bounds_nothing", "a_negated_equality_is_not_an_order"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s read more than a complement off a negation" % owner)
print("dogfood negated_guard_range: an early-return guard is an order, and its complement is all of it")
PY

# A lend that cannot outlive its call does not make the binding reachable later.
