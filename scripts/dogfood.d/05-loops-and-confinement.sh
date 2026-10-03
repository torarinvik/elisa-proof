# shellcheck shell=bash
# Part 5 of scripts/dogfood.sh; sourced in order by it, never run alone.
python3 - "$REPORT_DIR/aggregate_local_symbol.json" "$REPORT_DIR/rejected_aggregate_local_symbol.json" <<'PY'
import json
import sys

places, owed = sys.argv[1:]
with open(places, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: aggregate local fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("a_container_local_from_a_call", "a_struct_local_from_a_call", "a_loop_over_a_call_local"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost the places under an aggregate local" % owner)
with open(owed, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: aggregate local boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("an_unguarded_index_is_still_owed", "a_guard_over_another_collection", "a_field_is_not_a_claim", "a_rebound_local_loses_its_guard"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s read a claim out of an aggregate local's symbol" % owner)
print("dogfood aggregate_local_symbol: an aggregate local's places are places, and its symbol claims nothing")
PY

# A collection builtin writes its receiver during its own call and leaves nothing behind, so the
# receiver is not part of what escapes the call; every other route to the collection still is.
python3 - "$REPORT_DIR/collection_builtin_extent.json" "$REPORT_DIR/rejected_collection_builtin_extent.json" <<'PY'
import json
import sys

kept, owed = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: collection builtin fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("push_then_loop", "shrink_then_loop", "two_collections"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost the range of a collection it only pushed to" % owner)
with open(owed, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: collection builtin boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("a_lend_still_escapes", "a_push_in_the_body_still_writes", "a_push_still_changes_the_count", "a_pushed_lend_still_escapes"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s read a reach a collection builtin does not remove" % owner)
print("dogfood collection_builtin_extent: a push is a write, not a reach that outlives its call")
PY

# A counter keeps its own value across its update, and the fresh symbol that records it claims
# nothing beyond the update itself.
python3 - "$REPORT_DIR/loop_counter_invariant.json" "$REPORT_DIR/rejected_loop_counter_invariant.json" <<'PY'
import json
import sys

kept, owed = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: counter fixture did not prove cleanly")
verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}
for owner in ("bounded_counter", "walk_to_limit", "increment_keeps_its_value", "two_counters"):
    if owner not in verified:
        raise SystemExit("dogfood failed: %s lost a counter's value across its own update" % owner)
with open(owed, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: counter boundary fixture did not fail cleanly")
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("an_increment_without_a_peer", "a_non_unit_step", "a_false_invariant", "a_counter_is_not_a_total", "a_pre_update_fact_is_not_current"):
    if reasons.get(owner) != "body-unverified":
        raise SystemExit("dogfood failed: %s read more out of a rebind than the update" % owner)
print("dogfood loop_counter_invariant: a counter's update is recorded, and records only itself")
PY

# A call boundary and a branch join forget only what a callee or an arm can rewrite: a by-value
# scalar nothing references keeps its value, a referenced one and a value over it do not.
python3 - "$REPORT_DIR/call_boundary_binding.json" "$REPORT_DIR/rejected_call_boundary_binding.json" <<'PY'
import json
import sys

kept, dropped = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: call boundary fixture did not replay cleanly")
unproven = [goal["name"] for goal in report["goals"] if not goal["proven"]]
if unproven:
    raise SystemExit("dogfood failed: a binding no callee can reach was forgotten at the boundary: %s" % unproven)
proven = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] == "goal"}
required = {"loop_binder_survives_a_declaration_call", "value_survives_a_declaration_call", "value_survives_an_assignment_call", "value_survives_a_statement_call", "loop_binder_survives_a_guarded_call", "value_survives_a_returning_branch"}
if not required <= proven:
    raise SystemExit("dogfood failed: call boundary fixture is missing goals: %s" % sorted(required - proven))
if report["findings"]:
    raise SystemExit("dogfood failed: unexpected findings at the call boundary: %s" % sorted({f["kind"] for f in report["findings"]}))
with open(dropped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: rejected call boundary fixture did not fail cleanly")
owners = {finding["name"] for finding in report["findings"] if finding["kind"] == "ensure-unproven"}
expected = {"referenced_value_must_not_survive", "value_over_a_referenced_binding_must_not_follow_it", "referenced_value_must_not_survive_a_statement_call", "value_overwritten_in_one_arm_must_not_survive", "value_overwritten_in_the_surviving_arm_must_not_survive"}
if owners != expected:
    raise SystemExit("dogfood failed: a rewritable binding survived the boundary: %s" % sorted(expected - owners))
print("dogfood call_boundary_binding: a call and a join forget only what can be rewritten")
PY

# An impure call on the right of a short-circuit is modelled as a call that may have run: checked
# and havocked as if it did, with nothing only the run establishes surviving.
python3 - "$REPORT_DIR/short_circuit_call.json" "$REPORT_DIR/rejected_short_circuit_call.json" <<'PY'
import json
import sys

kept, dropped = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["summary"]["semantic_errors"] or report["replay"]["gaps"] or report["findings"]:
    raise SystemExit("dogfood failed: short-circuit fixture did not prove cleanly")
verified = {declaration["name"] for declaration in report["declaration_details"] if declaration["kind"] == "function" and declaration["verified"]}
required = {"guard_with_a_skippable_call", "declaration_with_a_skippable_call", "return_with_a_skippable_call", "caller_of_the_returning_shape"}
if not required <= verified:
    raise SystemExit("dogfood failed: a short-circuited call still invalidates its path: %s" % sorted(required - verified))
with open(dropped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: rejected short-circuit fixture did not fail cleanly")
kinds = {(finding["name"], finding["kind"]) for finding in report["findings"]}
expected = {("skipped_call_must_not_establish_and", "ensure-unproven"), ("skipped_call_must_not_establish_or", "ensure-unproven"), ("skipped_call_must_not_establish_a_guard", "ensure-unproven"), ("pre_call_value_must_not_survive", "ensure-unproven"), ("skipped_requires_is_still_checked", "call-requires-unproven"), ("mutable_left_fact_must_not_survive", "ensure-unproven")}
if kinds != expected:
    raise SystemExit("dogfood failed: unexpected verdicts around a skipped call: %s" % sorted(kinds ^ expected))
print("dogfood short_circuit_call: a skipped call is havocked and checked but establishes nothing")
PY

# A conjunct beside a placeholder is a branch fact in its own right and replays; the conjunct
# carrying the placeholder is recorded in no form, and nothing is derived from the condition.
python3 - "$REPORT_DIR/branch_conjunct_placeholder.json" "$REPORT_DIR/rejected_branch_conjunct_placeholder.json" <<'PY'
import json
import sys

kept, dropped = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"] or report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: placeholder conjunct fixture did not replay cleanly")
goals = [goal for goal in report["goals"] if goal["name"] == "conjunct_beside_a_placeholder" and goal["rule"] == "goal"]
if not goals or not all(goal["proven"] and goal["replay_status"] == "replayed" for goal in goals):
    raise SystemExit("dogfood failed: a conjunct beside a placeholder did not prove and replay")
if any(origin["kind"] == "branch-conjunct" for goal in goals for origin in goal["fact_origins"]):
    raise SystemExit("dogfood failed: a conjunct was derived from an inadmissible condition")
with open(dropped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: rejected placeholder fixture did not fail cleanly")
goals = [goal for goal in report["goals"] if goal["name"] == "placeholder_conjunct_must_not_become_a_fact" and goal["rule"] == "goal"]
if not goals or all(goal["proven"] for goal in goals) or any(origin["kind"] == "branch-conjunct" for goal in goals for origin in goal["fact_origins"]):
    raise SystemExit("dogfood failed: a placeholder conjunct became a fact")
print("dogfood branch_conjunct_placeholder: a conjunct beside a placeholder is a fact of its own, the placeholder is not")
PY

# A loop body is checked for an arbitrary iteration: a rewritten binding's entry value never
# stands in for it, and what holds on every iteration is still known.
python3 - "$REPORT_DIR/loop_entry_state.json" "$REPORT_DIR/rejected_loop_entry_state.json" <<'PY'
import json
import sys

kept, dropped = sys.argv[1:]
with open(kept, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: loop entry fixture did not replay cleanly")
goals = [goal for goal in report["goals"] if goal["rule"] != "resource-safety"]
if not goals or not all(goal["proven"] for goal in goals):
    raise SystemExit("dogfood failed: a loop body lost a fact that holds on every iteration: %s" % [goal["name"] for goal in goals if not goal["proven"]])
with open(dropped, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: rejected loop entry fixture did not fail cleanly")
proven = {}
for goal in report["goals"]:
    if goal["rule"] == "goal":
        proven.setdefault(goal["name"], []).append(goal["proven"])
if proven["entry_value_must_not_reach_the_body"] != [False] or proven["entry_value_must_not_reach_an_uncaptured_body"] != [False]:
    raise SystemExit("dogfood failed: a loop body used the entry value of a binding it rewrites")
if False not in proven["false_invariant_must_not_be_preserved"] or all(proven["break_must_not_yield_the_exit_condition"]):
    raise SystemExit("dogfood failed: a false invariant was preserved, or a break yielded the exit condition")
print("dogfood loop_entry_state: a loop body sees an arbitrary iteration, never the entry values")
PY

# An invariant-less loop still assumes its own condition in the body, and a shared borrow keeps
# its element count across a call -- unless the program declares a mutable global, which is the
# one path a shared borrow does not exclude.
python3 - "$REPORT_DIR/loop_condition_facts.json" "$REPORT_DIR/rejected_loop_condition_facts.json" "$REPORT_DIR/rejected_shared_extent_global.json" <<'PY'
import json
import sys

bounded, unbounded, aliased = sys.argv[1:]
with open(bounded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: loop condition fixture did not replay cleanly")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for entry in (("while_condition_bounds_the_body", "index-upper"), ("shared_extent_survives_a_call_in_the_body", "index-upper"), ("shared_extent_survives_a_call", "index-upper")):
    if entry not in proven:
        raise SystemExit("dogfood failed: %s did not reach the indexed access" % (entry,))
kinds = {finding["kind"] for finding in report["findings"]}
if kinds != {"loop-invariant-missing"}:
    raise SystemExit("dogfood failed: unexpected findings around a bounded loop: %s" % sorted(kinds))
with open(unbounded, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: loop condition boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for entry in (("unrelated_condition_proves_no_bound", "index-upper"), ("mutable_extent_must_not_survive_a_call", "index-upper"), ("entry_value_must_not_reach_the_body", "goal")):
    if goals.get(entry) is not False:
        raise SystemExit("dogfood failed: %s claimed more than the loop condition gives" % (entry,))
with open(aliased, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: shared extent global fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
if goals.get(("borrowed_extent_must_not_survive", "index-upper")) is not False:
    raise SystemExit("dogfood failed: a shared extent survived a mutable global write")
print("dogfood loop_condition_facts: the body assumes its condition and a shared extent, and nothing more")
PY

# Structural transitivity is a producer rule with a kernel counterpart: every chained goal must
# replay, and no chain may be built out of a user comparison.
python3 - "$REPORT_DIR/comparison_chain.json" "$REPORT_DIR/rejected_comparison_chain.json" <<'PY'
import json
import sys

chained, refused = sys.argv[1:]
with open(chained, encoding="utf-8") as handle:
    report = json.load(handle)
if report["verification_state"] != "proved" or report["findings"]:
    raise SystemExit("dogfood failed: comparison chain fixture did not prove clean")
if report["replay"]["gaps"] or report["replay"]["certificates"] != report["replay"]["replayed"]:
    raise SystemExit("dogfood failed: a chained goal did not replay in the kernel")
if report["trust"]["trusted_assumptions"]:
    raise SystemExit("dogfood failed: a chained goal rested on a trusted assumption")
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: comparison chain boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("struct_order_is_not_transitive", "struct_non_strict_order_is_not_transitive"):
    if goals.get((owner, "goal")) is True:
        raise SystemExit("dogfood failed: a user-defined struct order authorized a transitivity proof")
    if any(declaration["name"] == owner and declaration["verified"] for declaration in report["declaration_details"]):
        raise SystemExit("dogfood failed: a declaration with unsupported struct ordering was verified")
    if (owner, "goal") not in goals and not any(finding["kind"] == "contract-proposition-type" and finding["name"] == owner for finding in report["findings"]):
        raise SystemExit("dogfood failed: unsupported struct ordering was not rejected at admission")
for entry in (("non_strict_chain_gives_no_strict_goal", "goal"), ("wrong_direction_chain", "goal")):
    if goals.get(entry) is not False:
        raise SystemExit("dogfood failed: %s was chained without the order to do it" % (entry,))
print("dogfood comparison_chain: transitivity replays in the kernel and is refused for a user comparison")
PY

# A summary that rests on an over-approximated construct must still replay, must still be refused
# for any unproven obligation, and must never be reported as plain "verified".
python3 - "$REPORT_DIR/widened_state_summary.json" "$REPORT_DIR/rejected_widened_state_summary.json" <<'PY'
import json
import sys

widened, refused = sys.argv[1:]
with open(widened, encoding="utf-8") as handle:
    report = json.load(handle)
if report["summary"]["semantic_errors"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: widened-state summary fixture did not replay cleanly")
if report["verification_state"] != "unknown":
    raise SystemExit("dogfood failed: a widened-state contract was reported as more than unknown")
if [goal for goal in report["goals"] if not goal["proven"]]:
    raise SystemExit("dogfood failed: the widened-state summary fixture left a goal open")
proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}
for entry in (("caller_may_use_that_summary", "goal"), ("caller_may_use_that_one_too", "goal"), ("two_levels_above", "goal")):
    if entry not in proven:
        raise SystemExit("dogfood failed: %s could not use a widened-state summary" % (entry,))
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("missing_invariant_is_havocked_too", "caller_may_use_that_one_too", "two_levels_above"):
    if reasons.get(owner) != "contract-verified-widened-state":
        raise SystemExit("dogfood failed: %s was not reported as contract-verified-widened-state" % owner)
# A `for` over a collection is modelled by the loop handler whether or not the source spells a
# capture list, so this pair is plainly verified and no longer exercises the widening.
for owner in ("loop_is_havocked_but_the_contract_holds", "caller_may_use_that_summary"):
    if reasons.get(owner) != "verified":
        raise SystemExit("dogfood failed: %s was not reported as verified" % owner)
# The marking follows the call graph and stops there: a function that reaches only fully checked
# code still says "verified", so the two reasons stay distinguishable.
for owner in ("untouched_leaf", "untouched_caller"):
    if reasons.get(owner) != "verified":
        raise SystemExit("dogfood failed: %s lost a plain verified contract to the widened marking" % owner)
with open(refused, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: widened-state boundary fixture did not fail cleanly")
owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}
for entry in (("caller_gets_no_summary", "function-summary-unverified"), ("caller_gets_no_summary_from_an_unproven_index", "function-summary-unverified"), ("caller_gets_no_frame", "function-summary-unverified")):
    if entry not in owners:
        raise SystemExit("dogfood failed: %s imported a summary from an unproven callee" % (entry,))
# A summary carries a frame as well as an `ensure`, so both halves have to be checked through the
# construct the widening rule forgives.
for entry in (("writes_outside_its_frame", "frame-write-outside"), ("breaks_what_it_preserves", "frame-preserve-write")):
    if entry not in owners:
        raise SystemExit("dogfood failed: %s exported a frame its captured block breaks" % (entry,))
reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}
for owner in ("unproven_ensure_with_a_loop", "unproven_index", "writes_outside_its_frame", "breaks_what_it_preserves"):
    if reasons.get(owner) in ("verified", "contract-verified-widened-state"):
        raise SystemExit("dogfood failed: %s was reported as carrying a usable contract" % owner)
# The pair the whole relaxation rests on: an unframed widened callee is accepted, and the call
# boundary still has to take its caller's stale fact away.
if reasons.get("unframed_widened") != "contract-verified-widened-state":
    raise SystemExit("dogfood failed: an unframed widened callee did not export its summary")
if ("caller_must_lose_the_fact", "ensure-unproven") not in owners:
    raise SystemExit("dogfood failed: a fact survived a call into a widened callee that overwrites it")
print("dogfood widened_state_summary: an over-approximated construct keeps the summary, an unproven obligation does not")
PY

# The rendered proof must agree with the report for *every* goal, not a sampled one: `qed` appears
# exactly when the goal is proven and its certificate replayed, `unchecked` when it is proven
# without one, and `open` otherwise. A renderer that overstated a verdict would be a false claim in
# the most human-facing surface there is.
for render_example in condition_call_positions rejected_condition_call_positions writable_lend_calls region_lend_calls; do
    python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/$render_example.elisa" "$REPORT_DIR/$render_example.json" <<'PY'
import json
import subprocess
import sys

binary, source, report_path = sys.argv[1:]
with open(report_path, encoding="utf-8") as handle:
    report = json.load(handle)
replayed = {index for index, certificate in enumerate(report["certificates"]) if certificate["replayed"]}
for goal_id, goal in enumerate(report["goals"]):
    rendered = subprocess.run([binary, "--proof", str(goal_id), source], capture_output=True, text=True)
    if rendered.returncode != 0:
        raise SystemExit("dogfood failed: --proof %d exited %d" % (goal_id, rendered.returncode))
    text = rendered.stdout
    kernel_backed = goal["proven"] and goal.get("replay_status") == "replayed"
    has_qed = "\nqed\n" in text
    if has_qed != kernel_backed:
        raise SystemExit("dogfood failed: goal %d rendered qed=%s but kernel_backed=%s in %s" % (goal_id, has_qed, kernel_backed, source))
    if not goal["proven"]:
        if "\nopen " not in text or "    unproved: " not in text:
            raise SystemExit("dogfood failed: unproven goal %d did not render an open block" % goal_id)
    elif not kernel_backed and "\nunchecked " not in text:
        raise SystemExit("dogfood failed: producer-only goal %d did not render as unchecked" % goal_id)
    givens = sum(1 for line in text.splitlines() if line.startswith("    given "))
    if givens != len(goal.get("facts", [])):
        raise SystemExit("dogfood failed: goal %d rendered %d hypotheses for %d recorded facts" % (goal_id, givens, len(goal.get("facts", []))))
    if text.count("    show ") != 1:
        raise SystemExit("dogfood failed: goal %d did not render exactly one conclusion" % goal_id)
PY
done
printf 'dogfood proof_render: every rendered block matches the report verdict and hypothesis set\n'

# Round-trip: every rendered block must check clean against its own source, and mutating any single
# line of it must be reported as a divergence. A checker that accepted an edited block would make
# the readable surface forgeable.
for render_example in condition_call_positions rejected_condition_call_positions; do
    python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/$render_example.elisa" "$REPORT_DIR/$render_example.json" "$REPORT_DIR" <<'PY'
import json
import os
import subprocess
import sys

binary, source, report_path, workdir = sys.argv[1:]
with open(report_path, encoding="utf-8") as handle:
    report = json.load(handle)
block_path = os.path.join(workdir, "roundtrip.proof")
for goal_id in range(len(report["goals"])):
    rendered = subprocess.run([binary, "--proof", str(goal_id), source], capture_output=True, text=True).stdout
    with open(block_path, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    checked = subprocess.run([binary, "--check-proof", block_path, source], capture_output=True, text=True)
    if checked.returncode != 0 or json.loads(checked.stdout)["status"] != "matches":
        raise SystemExit("dogfood failed: goal %d did not round-trip in %s" % (goal_id, source))
    lines = rendered.splitlines()
    for line_index in range(len(lines)):
        mutated = list(lines)
        mutated[line_index] = mutated[line_index] + " tampered"
        with open(block_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(mutated) + "\n")
        checked = subprocess.run([binary, "--check-proof", block_path, source], capture_output=True, text=True)
        if checked.returncode == 0:
            raise SystemExit("dogfood failed: goal %d accepted a block tampered at line %d" % (goal_id, line_index + 1))
        payload = json.loads(checked.stdout)
        if payload["status"] == "matches":
            raise SystemExit("dogfood failed: goal %d reported a tampered block as matching" % goal_id)
PY
done
printf 'dogfood proof_check: rendered blocks round-trip and any edited line is reported\n'

# A human-written script must gain no path of its own: translating it into the tactic interchange
# and running that must give the identical verdict, and every malformed shape must be refused.
script_text_output="$REPORT_DIR/script_text.json"
script_json_output="$REPORT_DIR/script_json.json"
"$ROOT_DIR/build/elisa-proof" --script "$ROOT_DIR/examples/proof_script_target.proof" "$ROOT_DIR/examples/verified.elisa" >"$script_text_output"
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target.json" "$ROOT_DIR/examples/verified.elisa" >"$script_json_output"
if ! cmp -s "$script_text_output" "$script_json_output"; then
    printf 'dogfood failed: a text proof script diverged from its JSON equivalent\n' >&2
    exit 1
fi
python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/verified.elisa" "$REPORT_DIR" <<'PY'
import json
import os
import subprocess
import sys

binary, source, workdir = sys.argv[1:]
script_path = os.path.join(workdir, "probe.proof")
refused = {
    "unknown action": "# goal 7\nproof p:\n    by nosuchtactic\nqed\n",
    "unrecognized line": "# goal 7\nproof p:\n    bye assumption\nqed\n",
    "no steps": "# goal 7\nproof p:\nqed\n",
    "trailing text after a step": "# goal 7\nproof p:\n    by assumption extra\nqed\n",
    "no goal header": "proof p:\n    by assumption\nqed\n",
    "step that does not close the goal": "# goal 7\nproof p:\n    by intro\nqed\n",
}
for label, text in refused.items():
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    result = subprocess.run([binary, "--script", script_path, source], capture_output=True, text=True)
    payload = json.loads(result.stdout)
    if payload["status"] == "proved" or payload["tactic"]["solved"]:
        raise SystemExit("dogfood failed: proof script admitted despite %s" % label)
# An invented hypothesis is documentation, not an assumption: it must not change the verdict.
with open(script_path, "w", encoding="utf-8") as handle:
    handle.write("# goal 7\nproof p:\n    given 1 == 2\n    by assumption\nqed\n")
invented = json.loads(subprocess.run([binary, "--script", script_path, source], capture_output=True, text=True).stdout)
with open(os.path.join(workdir, "script_text.json"), encoding="utf-8") as handle:
    baseline = json.load(handle)
if invented["tactic"] != baseline["tactic"] or invented["state"] != baseline["state"]:
    raise SystemExit("dogfood failed: a written hypothesis changed the proof state")
PY
printf 'dogfood proof_script: a written script runs the checked engine and nothing else\n'

# Repair proposes and the kernel disposes. Across every goal of a proved fixture and an adversarial
# one, a repair that reports success must emit a script that re-runs and replays, and a repair that
# reports failure must emit none — and no goal of the adversarial fixture may be repaired at all.
python3 - "$ROOT_DIR/build/elisa-proof" "$REPORT_DIR" <<'PY'
import json
import os
import subprocess
import sys

binary, workdir = sys.argv[1:]
root = os.path.dirname(os.path.dirname(binary))
script_path = os.path.join(workdir, "repair.proof")
for source_name, expect_any in (("examples/verified.elisa", True), ("examples/rejected_repair_target.elisa", False)):
    source = os.path.join(root, source_name)
    report = json.loads(subprocess.run([binary, "--json", source], capture_output=True, text=True).stdout)
    repaired_any = False
    for goal_id in range(len(report["goals"])):
        result = subprocess.run([binary, "--repair", str(goal_id), source], capture_output=True, text=True)
        payload = json.loads(result.stdout)
        if payload["status"] == "repaired":
            repaired_any = True
            if result.returncode != 0 or not payload["script"]:
                raise SystemExit("dogfood failed: repaired goal %d emitted no script" % goal_id)
            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(payload["script"])
            rerun = subprocess.run([binary, "--script", script_path, source], capture_output=True, text=True)
            verdict = json.loads(rerun.stdout)
            if rerun.returncode != 0 or not verdict["tactic"]["solved"] or not verdict["tactic"]["kernel_replayed"]:
                raise SystemExit("dogfood failed: repair for goal %d did not re-check in %s" % (goal_id, source_name))
        else:
            if payload["script"] is not None:
                raise SystemExit("dogfood failed: unrepaired goal %d still emitted a script" % goal_id)
            if result.returncode == 0:
                raise SystemExit("dogfood failed: unrepaired goal %d exited zero" % goal_id)
    if repaired_any != expect_any:
        raise SystemExit("dogfood failed: %s repaired=%s, expected %s" % (source_name, repaired_any, expect_any))
PY
printf 'dogfood proof_repair: every proposal the search admits re-runs and replays\n'

# The whole-file walk must agree with the per-goal one exactly: the same goals, the same verdicts,
# the same scripts. A batch that disagreed with the single-goal answer would mean one of them is
# reporting something the engine did not decide.
python3 - "$ROOT_DIR/build/elisa-proof" <<'PY'
import json
import os
import subprocess
import sys

binary = sys.argv[1]
root = os.path.dirname(os.path.dirname(binary))
for source_name in ("examples/verified.elisa", "examples/rejected_repair_target.elisa"):
    source = os.path.join(root, source_name)
    report = json.loads(subprocess.run([binary, "--json", source], capture_output=True, text=True).stdout)
    batch = json.loads(subprocess.run([binary, "--repair-all", source], capture_output=True, text=True).stdout)
    expected = [index for index, goal in enumerate(report["goals"]) if not goal["proven"]]
    if [entry["goal_id"] for entry in batch["goals"]] != expected:
        raise SystemExit("dogfood failed: %s batch did not walk exactly the unresolved goals" % source_name)
    if batch["summary"]["unresolved"] != len(expected):
        raise SystemExit("dogfood failed: %s batch miscounted unresolved goals" % source_name)
    for entry in batch["goals"]:
        single = json.loads(subprocess.run([binary, "--repair", str(entry["goal_id"]), source], capture_output=True, text=True).stdout)
        if single["status"] != entry["status"] or single["script"] != entry["script"]:
            raise SystemExit("dogfood failed: %s goal %d disagrees between --repair and --repair-all" % (source_name, entry["goal_id"]))
    repaired = sum(1 for entry in batch["goals"] if entry["status"] == "repaired")
    if repaired != batch["summary"]["repaired"]:
        raise SystemExit("dogfood failed: %s batch summary does not match its own entries" % source_name)
PY
printf 'dogfood proof_repair_batch: the whole-file walk agrees with the per-goal answer\n'


# Exercise the same admission routine as native Elisa code. This is separate from the report
# checker: malformed input must be rejected by the compiled source-neutral module too.
runtime_dir="$REPORT_DIR/runtime-arena"
mkdir -p "$runtime_dir"
runtime_source="$SNAPSHOT_COMPILER/elisacore_std/native_runtime_support.elisa"
if [[ ! -f "$runtime_source" ]]; then
    printf 'dogfood failed: Elisa runtime source is missing for executable arena harness\n' >&2
    exit 1
fi
"$COMPILER" -emit obj -O0 -o "$runtime_dir/program.o" "$ROOT_DIR/examples/kernel_arena_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/program" "$runtime_dir/program.o" "$RUNTIME_OBJ"
else
    "$COMPILER" -emit obj -O0 -o "$runtime_dir/runtime-support.o" "$runtime_source" >/dev/null 2>&1
    link_native "$runtime_dir/program" "$runtime_dir/program.o" "$runtime_dir/runtime-support.o"
fi
set +e
"$runtime_dir/program"
runtime_status=$?
set -e
if [[ "$runtime_status" -ne 0 ]]; then
    printf 'dogfood failed: executable arena admission suite failed (exit %s)\n' "$runtime_status" >&2
    exit 1
fi
printf 'dogfood arena_runtime: malformed arenas/resource places rejected and valid DAG sharing accepted\n'

"$COMPILER" -emit obj -O0 -o "$runtime_dir/proposition-admission-runtime.o" "$ROOT_DIR/examples/kernel_proposition_admission_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/proposition-admission-runtime" "$runtime_dir/proposition-admission-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/proposition-admission-runtime" "$runtime_dir/proposition-admission-runtime.o" "$runtime_dir/runtime-support.o"
fi
set +e
"$runtime_dir/proposition-admission-runtime"
admission_status=$?
set -e
if [[ "$admission_status" -ne 0 ]]; then
    printf 'dogfood failed: native typed proposition-admission suite exited %s\n' "$admission_status" >&2
    exit 1
fi
printf 'dogfood proposition_admission_runtime: abstract atoms, typed source terms, and tactic boundaries passed\n'

"$COMPILER" -emit obj -O0 -o "$runtime_dir/comparison-runtime.o" "$ROOT_DIR/examples/kernel_comparison_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/comparison-runtime" "$runtime_dir/comparison-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/comparison-runtime" "$runtime_dir/comparison-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/comparison-runtime"
printf 'dogfood comparison_runtime: witnessed comparisons, typed negative constants, width-tagged unsigned literals, and every range-quantifier instance checked; unwitnessed reflexivity refused\n'

# Congruence closure is exercised against the kernel directly: every participating former must
# carry an equality, and every excluded former (call, move, address-of, namespace path, guarded
# access, quantifier) must refuse to, on both the dedicated rule and full goal replay.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/congruence-runtime.o" "$ROOT_DIR/examples/kernel_congruence_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/congruence-runtime" "$runtime_dir/congruence-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/congruence-runtime" "$runtime_dir/congruence-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/congruence-runtime"
printf 'dogfood congruence_runtime: participating formers carried equalities and excluded formers refused\n'

# Propositional fact projection is exercised against the kernel directly: a conjunction entails
# each conjunct, a negated disjunction entails each negated disjunct, a double negation cancels,
# and the dual forms - a disjunction, a negated conjunction - must stay refused in both signs.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/projection-runtime.o" "$ROOT_DIR/examples/kernel_projection_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/projection-runtime" "$runtime_dir/projection-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/projection-runtime" "$runtime_dir/projection-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/projection-runtime"
printf 'dogfood projection_runtime: conjunct and negated-disjunct projection admitted, duals refused\n'

# Declared effect containment is checked against the kernel directly: contained rows admitted,
# uncontained rows refused, and every malformed effect graph rejected rather than interpreted.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/effect-runtime.o" "$ROOT_DIR/examples/kernel_effect_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/effect-runtime" "$runtime_dir/effect-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/effect-runtime" "$runtime_dir/effect-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/effect-runtime"
printf 'dogfood effect_runtime: contained rows admitted and uncontained or malformed rows refused\n'

# Bootstrap coverage: compile the runtime with stage0 as well; an installed stage1
# runtime is not an implicit bootstrap dependency. The reduced resource trace
# guards the stage0 miscompile of allocations made through an unannotated mutable
# reference inside a region-polymorphic function (see AUDIT.md); the full arena
# harness then confirms the whole replay layer under the bootstrap compiler.
