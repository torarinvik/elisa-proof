# shellcheck shell=bash
# Part 3 of scripts/dogfood.sh; sourced in order by it, never run alone.
# as a gap while the kernel read a construction's type name as a runtime value.
python3 - "$REPORT_DIR/region_call_summary.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: a region-polymorphic callee summary did not compose")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a region certificate was left unreplayed")
kinds = {node["kind"] for node in report["kernel"]["nodes"]}
for kind in ("resource-region-alloc", "construct", "record-update", "resource-call"):
    if kind not in kinds:
        raise SystemExit("dogfood failed: %s never reached the arena" % kind)
print("dogfood region_call_summary: a constructed type is not a value, a record base still is")
PY

# An executable call in a branch condition is modelled wherever it certainly runs. A call that may
# be skipped, and a fact naming an impure call that a later obligation names again, stay refused.
python3 - "$REPORT_DIR/condition_call_positions.json" "$REPORT_DIR/rejected_condition_call_positions.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: unconditional condition calls did not prove cleanly")
names = {goal["name"] for goal in report["goals"] if goal["proven"]}
for name in ("negated_call", "compared_call", "short_circuit_left", "arithmetic_call", "guarded_index"):
    if name not in names:
        raise SystemExit("dogfood failed: %s did not enter a verified proof state" % name)
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0 or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: condition-call boundary fixture did not fail cleanly")
unsupported = {finding["name"] for finding in report["findings"] if finding["kind"] == "expression-unsupported"}
for name in ("conditional_call", "literal_field_call"):
    if name not in unsupported:
        raise SystemExit("dogfood failed: %s was admitted as an unconditional call" % name)
for name in ("right_of_and", "right_of_or"):
    if name in unsupported:
        raise SystemExit("dogfood failed: %s was refused instead of walked against a copy" % name)
if any(goal["proven"] and goal["rule"] == "index-upper" for goal in report["goals"]):
    raise SystemExit("dogfood failed: a guard naming an impure call discharged an index bound")
print("dogfood condition_call_positions: a condition call is modelled only where it certainly runs")
PY

# The product-sign tier must be stated identically by the producer and the kernel. Every accepted
# goal has to replay, and no refused shape may be concluded on either side.
python3 - "$REPORT_DIR/product_sign.json" "$REPORT_DIR/rejected_product_sign.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: product sign reasoning did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a product-sign certificate was left unreplayed")
names = {goal["name"] for goal in report["goals"] if goal["proven"]}
for name in ("nonnegative_product", "negative_operands", "mixed_operands", "strict_product", "strict_negative", "mirrored_forms"):
    if name not in names:
        raise SystemExit("dogfood failed: %s was not proven" % name)
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0 or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: product-sign boundary fixture did not fail cleanly")
if any(goal["proven"] and goal["rule"] != "resource-safety" for goal in report["goals"]):
    raise SystemExit("dogfood failed: an unsound product sign was concluded")
print("dogfood product_sign: a product's sign follows from its operands' signs and nothing else")
PY

# A frame-pinned lifetime is a claim about the caller's frame, not about a region, so the mapping
# names `@call-frame` and every such call must still replay. A refused shape must record no such
# mapping at all.
python3 - "$REPORT_DIR/frame_lifetime.json" "$REPORT_DIR/rejected_frame_lifetime.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: frame lifetime pinning did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a frame-pinned call was left unreplayed")
frame_maps = [node for node in report["kernel"]["nodes"] if node["kind"] == "resource-call-region" and node["secondary_name"] == "@call-frame"]
if not frame_maps:
    raise SystemExit("dogfood failed: no frame-pinned lifetime reached the arena")
if any(node["operator"] != "param" or not node["name"] for node in frame_maps):
    raise SystemExit("dogfood failed: a frame mapping is malformed")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0 or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: frame lifetime boundary fixture did not fail cleanly")
if any(node["kind"] == "resource-call-region" and node["secondary_name"] == "@call-frame" for node in report["kernel"]["nodes"]):
    raise SystemExit("dogfood failed: a lifetime was pinned to a frame that vouches for nothing")
print("dogfood frame_lifetime: a caller's frame pins a lifetime only for a place it holds outright")
PY

# The lend rule may carry a region-owned actual into a formal that declares no lifetime; the
# summary path may not. Both verdicts must replay.
python3 - "$REPORT_DIR/unnamed_lifetime_lend.json" "$REPORT_DIR/rejected_unnamed_lifetime_lend.json" <<'PY'
import json
import sys

lent, summarised = sys.argv[1:]
with open(lent, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: unnamed-lifetime lend did not replay cleanly")
resource = {goal["name"]: goal["proven"] for goal in report["goals"] if goal["rule"] == "resource-safety"}
for name in ("lends_region_value", "lends_region_value_exclusively", "lends_region_value_to_summary"):
    if resource.get(name) is not True:
        raise SystemExit("dogfood failed: %s was not admitted as a lend" % name)
kinds = {finding["kind"] for finding in report["findings"]}
if "region-call-opaque" in kinds or "borrow-call-opaque" in kinds:
    raise SystemExit("dogfood failed: an unnamed-lifetime lend was still reported opaque")
with open(summarised, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: summary-path boundary fixture did not fail cleanly")
if ("lends_region_value_to_a_keeper", "region-call-opaque") not in {(f["name"], f["kind"]) for f in report["findings"]}:
    raise SystemExit("dogfood failed: a callee that keeps what it is lent was admitted")
print("dogfood unnamed_lifetime_lend: a lend may carry a region the callee cannot name, unless it can keep it")
PY

# A captured block's body must be checked rather than skipped, and nothing established before it
# may survive the write-back.
python3 - "$REPORT_DIR/captured_block.json" "$REPORT_DIR/rejected_captured_block.json" <<'PY'
import json
import sys

checked, havocked = sys.argv[1:]
with open(checked, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: captured block fixture did not replay cleanly")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for entry in (("obligations_after_the_loop_are_checked", "index-upper"), ("obligations_inside_the_loop_are_checked", "index-upper")):
    if entry not in proven:
        raise SystemExit("dogfood failed: %s was not checked past the captured block" % (entry,))
if report["findings"]:
    raise SystemExit("dogfood failed: unexpected findings around a captured block: %s" % sorted({f["kind"] for f in report["findings"]}))
with open(havocked, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: captured block boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for entry in (("fact_must_not_survive", "goal"), ("value_must_not_survive", "goal"), ("obligation_inside_is_not_skipped", "index-upper")):
    if goals.get(entry) is not False:
        raise SystemExit("dogfood failed: %s survived a captured block's write-back" % (entry,))
print("dogfood captured_block: a captured block's body is checked and its write-back is havocked")
PY

# The write-back is over the capture list and the body's own writes, not the whole frame: a
# binding the block neither names nor writes keeps its value and its facts, and a binding it names
# or writes keeps neither.
python3 - "$REPORT_DIR/uncaptured_binding.json" "$REPORT_DIR/rejected_uncaptured_binding.json" <<'PY'
import json
import sys

kept, dropped = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: uncaptured binding fixture did not replay cleanly")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for entry in (("value_outside_the_capture_list_survives", "goal"), ("fact_outside_the_capture_list_survives", "goal")):
    if entry not in proven:
        raise SystemExit("dogfood failed: %s did not survive a captured block it is outside of" % (entry,))
if report["findings"]:
    raise SystemExit("dogfood failed: unexpected findings around an uncaptured binding: %s" % sorted({f["kind"] for f in report["findings"]}))
with open(dropped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: captured binding fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for entry in (("overwritten_binding_must_not_survive", "goal"), ("zero_iteration_fact_must_not_escape", "goal")):
    if goals.get(entry) is not False:
        raise SystemExit("dogfood failed: %s survived its own captured block" % (entry,))
print("dogfood uncaptured_binding: a captured block forgets its capture list and nothing else")
PY

python3 - "$REPORT_DIR/rejected_uncaptured_block_write.json" <<'PY'
import json
import sys

(path,) = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: uncaptured block write fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
written = (
    "assigned_without_being_captured",
    "assigned_under_a_branch",
    "written_through_a_reference",
    "assigned_in_a_nested_block",
    "fact_over_a_written_binding",
)
for owner in written:
    if (owner, "call-requires-unproven") not in owners:
        raise SystemExit("dogfood failed: %s discharged a precondition from a falsified state" % owner)
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s proved a goal from a falsified state" % owner)
kinds = {kind for _, kind in owners}
if kinds != {"call-requires-unproven"}:
    raise SystemExit("dogfood failed: unexpected findings around an uncaptured write: %s" % sorted(kinds))
print("dogfood rejected_uncaptured_block_write: a block write-back covers what its body writes")
PY

python3 - "$REPORT_DIR/loop_element_extent.json" "$REPORT_DIR/rejected_loop_element_extent.json" <<'PY'
import json
import sys

kept, resized = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: element extent fixture did not replay cleanly")
if {finding["kind"] for finding in report["findings"]} != {"loop-invariant-missing"}:
    raise SystemExit("dogfood failed: unexpected findings around an element write")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for owner in ("fill_in_place", "fill_under_a_branch", "fill_with_a_while", "a_recorded_count_survives", "aliased_elsewhere_but_not_in_the_body"):
    if (owner, "index-upper") not in proven:
        raise SystemExit("dogfood failed: %s lost the extent of the collection it writes" % owner)
with open(resized, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: element extent boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
for owner in ("a_push_in_the_body", "a_call_that_may_push", "a_whole_assignment", "one_whole_write_among_many", "a_reference_taken", "aliased_elsewhere_and_a_call_here"):
    if (owner, "index-upper-unproven") not in owners:
        raise SystemExit("dogfood failed: %s kept an extent its body can resize" % owner)
if any(goal["proven"] and goal["rule"] == "index-upper" for goal in report["goals"]):
    raise SystemExit("dogfood failed: a resized collection discharged an index bound")
print("dogfood loop_element_extent: an element write keeps the extent and nothing else does")
PY

python3 - "$REPORT_DIR/comparison_chain_equality.json" "$REPORT_DIR/rejected_comparison_chain_equality.json" <<'PY'
import json
import sys

chained, refused = sys.argv[1:]
with open(chained, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: equality chain fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: an equality-chain certificate was left unreplayed")
if report["trust"]["trusted_assumptions"]:
    raise SystemExit("dogfood failed: the equality chain rested on a trusted assumption")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for entry in (("paired_write", "index-upper"), ("equality_reversed", "index-upper"), ("non_strict_through_an_equality", "goal"), ("copy_into_a_paired_collection", "index-upper")):
    if entry not in proven:
        raise SystemExit("dogfood failed: %s did not reach its bound through an equality" % (entry,))
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: equality chain boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("struct_equality_is_not_an_order", "equality_alone_is_not_strict", "two_equalities_give_no_strict_goal", "inequality_is_not_a_step", "an_equality_to_the_wrong_term"):
    if owner == "struct_equality_is_not_an_order":
        if goals.get((owner, "goal")) is True:
            raise SystemExit("dogfood failed: an overloaded struct equality authorized an order proof")
        if any(declaration["name"] == owner and declaration["verified"] for declaration in report["declaration_details"]):
            raise SystemExit("dogfood failed: a declaration with unsupported struct comparison was verified")
        if (owner, "goal") not in goals and not any(finding["kind"] == "contract-proposition-type" and finding["name"] == owner for finding in report["findings"]):
            raise SystemExit("dogfood failed: unsupported struct comparison was not rejected at admission")
        continue
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s chained an equality it may not" % owner)
print("dogfood comparison_chain_equality: an equality is two non-strict steps and never a strict one")
PY

python3 - "$REPORT_DIR/region_extent_contract.json" "$REPORT_DIR/rejected_region_extent_contract.json" <<'PY'
import json
import sys

bounded, refused = sys.argv[1:]
with open(bounded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: region extent contract fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a region extent certificate was left unreplayed")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("bounded_without_indexing", "extent_in_an_ensure", "two_lifetimes", "indexes_under_its_own_precondition"):
    if reasons.get(owner) != "verified":
        raise SystemExit("dogfood failed: %s could not bound its own region-owned parameter" % owner)
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: region extent boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
for owner in ("struct_count_is_not_an_extent", "an_element_in_a_contract", "the_binding_itself", "a_field_of_an_element"):
    rejected_at_region_boundary = (owner, "region-contract-unsupported") in owners
    rejected_at_kernel_formation = (owner, "contract-proposition-type") in owners
    if not rejected_at_region_boundary and not rejected_at_kernel_formation:
        raise SystemExit("dogfood failed: %s entered a contract as if it were an extent" % owner)
    if any(goal["name"] == owner and goal["proven"] for goal in report["goals"]):
        raise SystemExit("dogfood failed: %s used a region-owned value to prove a contract" % owner)
    if any(declaration["name"] == owner and declaration["verified"] for declaration in report["declaration_details"]):
        raise SystemExit("dogfood failed: %s was verified after a region-owned contract term" % owner)
if ("shared_cannot_be_returned_mutable", "region-return-witness-unsupported") not in owners:
    raise SystemExit("dogfood failed: a shared binding witnessed a mutable-reference return")
print("dogfood region_extent_contract: a collection extent is contractable, a region-owned value is not")
PY

python3 - "$REPORT_DIR/region_statement_call.json" "$REPORT_DIR/rejected_region_statement_call.json" <<'PY'
import json
import sys

admitted, dropped = sys.argv[1:]
with open(admitted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: region statement call fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a region statement certificate was left unreplayed")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("pushes_into_a_region_collection", "pushes_through_a_region_struct", "pushes_without_a_lifetime"):
    if reasons.get(owner) != "verified":
        raise SystemExit("dogfood failed: %s was refused for naming a region-owned receiver" % owner)
with open(dropped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: region statement boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
if owners != {("discards_a_region_reference", "region-expression-unsupported")}:
    raise SystemExit("dogfood failed: a discarded region reference was admitted: %s" % sorted(owners))
print("dogfood region_statement_call: a call statement may name a region, its result may not carry one")
PY

python3 - "$REPORT_DIR/region_lifetime_free_callee.json" "$REPORT_DIR/rejected_region_lifetime_free_callee.json" <<'PY'
import json
import sys

lent, kept = sys.argv[1:]
with open(lent, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: lifetime-free callee fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a lifetime-free call certificate was left unreplayed")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("region_caller", "caller_that_writes", "region_caller_of_pusher"):
    if reasons.get(owner) != "verified":
        raise SystemExit("dogfood failed: %s could not hand a region-owned reference to a lifetime-free callee" % owner)
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: lifetime-free callee boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
if ("a_lifetime_free_callee_may_not_return_a_reference", "region-call-opaque") not in owners:
    raise SystemExit("dogfood failed: a callee that returns a reference was admitted from its declared modes")
if ("overlapping_mutable_actuals", "borrow-call-alias") not in owners:
    raise SystemExit("dogfood failed: two overlapping mutable actuals were admitted")
print("dogfood region_lifetime_free_callee: a lifetime-free callee may borrow a region, not keep it")
PY

python3 - "$REPORT_DIR/loop_binder_call_requires.json" "$REPORT_DIR/rejected_loop_binder_call_requires.json" <<'PY'
import json
import sys

bounded, unbounded = sys.argv[1:]
with open(bounded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: loop binder precondition fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a loop binder precondition certificate was left unreplayed")
with open(unbounded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: loop binder boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
for owner in ("one_past", "successor"):
    if (owner, "call-requires-unproven") not in owners:
        raise SystemExit("dogfood failed: %s established a precondition for an unbounded slot" % owner)
print("dogfood loop_binder_call_requires: a binder's bound reaches a callee precondition once")
PY

python3 - "$REPORT_DIR/call_guard_summaries.json" "$REPORT_DIR/rejected_call_guard_summaries.json" <<'PY'
import json
import sys

guarded, unguarded = sys.argv[1:]
with open(guarded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: call guard summary fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a call guard certificate was left unreplayed")
origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}
if "unit-resolution" not in origins:
    raise SystemExit("dogfood failed: the write after a call guard did not use a resolved fact")
with open(unguarded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: call guard boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
for owner in ("write_after_inverted_guard", "conditional_guard_call", "inverted_or_guard"):
    if (owner, "index-upper-unproven") not in owners:
        raise SystemExit("dogfood failed: %s bounded an access its guard call does not certify" % owner)
print("dogfood call_guard_summaries: a pure guard call bounds exactly the path it certifies")
PY

python3 - "$REPORT_DIR" <<'PY'
import json
import os
import sys

report_dir = sys.argv[1]
cases = (
    ("disequality_bounds", {('interior', 'ensure-unproven'), ('not_endpoint', 'ensure-unproven')}),
    ("conditional_equality_split", {('clamp_off_by_one', 'ensure-unproven')}),
    ("place_aliases", {('other_element', 'ensure-unproven')}),
    ("field_places", {('non_strict', 'index-upper-unproven'), ('other_field', 'index-upper-unproven'), ('other_record', 'index-upper-unproven')}),
    ("typed_wide_constants", {('wrapped_bound', 'ensure-unproven'), ('off_by_one', 'ensure-unproven'), ('wide_then_arm', 'ensure-unproven')}),
    ("complemented_else_arms", {('wrong_complement', 'ensure-unproven'), ('then_arm_unguarded', 'ensure-unproven'), ('weak_complement', 'ensure-unproven'), ('conjunction_complement', 'ensure-unproven')}),
    ("guarded_differences", {('modular_sum_fact', 'ensure-unproven'), ('modular_sum_bound', 'index-upper-unproven'), ('unguarded_difference', 'ensure-unproven'), ('one_past_the_span', 'ensure-unproven'), ('one_past_in_text', 'index-upper-unproven')}),
    ("literal_widths", {('plus_zero', 'ensure-unproven'), ('times_one', 'ensure-unproven'), ('wide_difference', 'ensure-unproven'), ('wide_sum', 'ensure-unproven'), ('negative_unsigned', 'ensure-unproven'), ('wide_signed', 'ensure-unproven'), ('below_signed_minimum', 'ensure-unproven'), ('wide_goal', 'ensure-unproven')}),
    ("shared_fixed_borrows", {('with_a_mutable_parameter', 'call-requires-unproven'), ('with_a_reference_field', 'call-requires-unproven')}),
    ("bound_call_summaries", {('stronger_than_the_summary', 'ensure-unproven'), ('unproven_precondition', 'call-requires-unproven'), ('unproven_precondition', 'ensure-unproven')}),
    ("value_call_arguments", {('container', 'ensure-unproven'), ('view', 'ensure-unproven'), ('hierarchy', 'ensure-unproven'), ('common_fields', 'ensure-unproven'), ('lent', 'ensure-unproven')}),
    ("call_result_places", {('wraps', 'ensure-unproven'), ('other_argument', 'ensure-unproven'), ('stale_argument', 'ensure-unproven')}),
    ("rebind_join", {('overshoot', 'ensure-unproven'), ('overshoot', 'invariant-not-preserved')}),
    ("conditional_conversions", {('widened_bound', 'ensure-unproven')}),
    ("conditional_call_arms", {('wrong_guard', 'call-requires-unproven'), ('skipped_arm', 'ensure-unproven'), ('called_nested_condition', 'expression-unsupported'), ('call_before_arm', 'expression-unsupported'), ('short_circuit_path', 'expression-unsupported'), ('nested_wrong_guard', 'call-requires-unproven')}),
    ("guarded_conditional_arms", {('wrong_arm', 'ensure-unproven'), ('weak_guard', 'ensure-unproven')}),
    ("captured_block_exit", {('unchecked', 'ensure-unproven'), ('broken', 'invariant-not-preserved'), ('broken', 'ensure-unproven')}),
    ("global_constant_loop_exit", {('last_slot', 'ensure-unproven')}),
    ("branch_join", {('not_always_kept', 'ensure-unproven'), ('replace_too_far', 'ensure-unproven'), ('stale_rebind', 'ensure-unproven')}),
    ("loop_state_joins", {('untrue_aggregate_bound', 'ensure-unproven'), ('escaping_arm', 'invariant-not-preserved'), ('arm_local_value', 'ensure-unproven'), ('growing_arm_local', 'invariant-not-preserved'), ('untrue_negated_order', 'ensure-unproven')}),
)
for name, owners in cases:
    with open(os.path.join(report_dir, name + ".json"), encoding="utf-8") as handle:
        report = json.load(handle)
    if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
        raise SystemExit("dogfood failed: %s did not prove cleanly" % name)
    if report["replay"]["certificates"] != report["replay"]["replayed"]:
        raise SystemExit("dogfood failed: a %s certificate was left unreplayed" % name)
    with open(os.path.join(report_dir, "rejected_" + name + ".json"), encoding="utf-8") as handle:
        report = json.load(handle)
    if report["status"] != "failed" or report["replay"]["gaps"]:
        raise SystemExit("dogfood failed: rejected_%s did not fail cleanly" % name)
    found = {(finding["name"], finding["kind"]) for finding in report["findings"]}
    if not owners <= found:
        raise SystemExit("dogfood failed: rejected_%s proved %s" % (name, sorted(owners - found)))
print("dogfood fact_transfer: disequality, conditional, alias, constant and join facts transfer only where sound")
PY

python3 - "$REPORT_DIR/short_circuit_guard.json" "$REPORT_DIR/rejected_short_circuit_guard.json" <<'PY'
import json
import sys

guarded, unguarded = sys.argv[1:]
with open(guarded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: short-circuit guard fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a short-circuit guard certificate was left unreplayed")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for owner in ("guarded_and", "guarded_or", "guarded_if", "guarded_early_return", "guards_two_reads"):
    if (owner, "index-upper") not in proven:
        raise SystemExit("dogfood failed: %s did not discharge its bound from its own guard" % owner)
with open(unguarded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: short-circuit guard boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
for owner in ("off_by_one", "guards_another_name", "or_runs_when_the_guard_fails", "guard_comes_after", "guard_has_a_call"):
    if (owner, "index-upper-unproven") not in owners:
        raise SystemExit("dogfood failed: %s bounded something its guard does not guard" % owner)
if any(goal["proven"] and goal["rule"] == "index-upper" for goal in report["goals"]):
    raise SystemExit("dogfood failed: a misplaced guard discharged an index bound")
print("dogfood short_circuit_guard: a guard bounds the operand it guards and nothing else")
PY

python3 - "$REPORT_DIR/bound_propagation.json" "$REPORT_DIR/rejected_bound_propagation.json" <<'PY'
import json
import sys

derived, invented = sys.argv[1:]
with open(derived, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: bound propagation fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a propagated-bound certificate was left unreplayed")
if report["trust"]["trusted_assumptions"]:
    raise SystemExit("dogfood failed: bound propagation rested on a trusted assumption")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for owner in ("increment_under_a_bounded_limit", "increment_through_a_chain", "lower_bound_travels", "unsigned_increment_under_a_strict_peer", "unsigned_increment_under_a_reversed_peer", "strict_fact_needs_no_upper_bound", "strict_fact_needs_no_related_bound"):
    if (owner, "goal") not in proven:
        raise SystemExit("dogfood failed: %s did not reach the overflow guard with its interval" % owner)
with open(invented, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: bound propagation boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("unsigned_step_of_two", "unsigned_increment_under_a_non_strict_peer", "unsigned_peer_of_another_name", "non_strict_premise_is_not_shiftable"):
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s was given an interval nothing established" % owner)
print("dogfood bound_propagation: a constraint carries an interval it already implies, and no other")
PY

python3 - "$REPORT_DIR/strict_shift.json" "$REPORT_DIR/rejected_strict_shift.json" <<'PY'
import json
import sys

shifted, refused = sys.argv[1:]
with open(shifted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: strict shift fixture did not prove cleanly")
if report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a strict-shift certificate was left unreplayed")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for owner in ("shift_to_a_field", "shift_to_a_name", "shift_from_a_reversed_fact", "shift_to_a_collection_extent"):
    if (owner, "goal") not in proven:
        raise SystemExit("dogfood failed: %s did not shift its strict fact" % owner)
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: strict shift boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("needs_a_strict_fact", "gives_no_strict_conclusion", "moves_by_one_only", "bounds_another_term", "another_collection_extent"):
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s took a shift that does not follow" % owner)
print("dogfood strict_shift: a strict fact shifts by one, non-strictly, to its own bound")
PY

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
