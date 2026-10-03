# shellcheck shell=bash
# Part 8 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
if [[ "$unsigned_nonnegative_sum_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a nonnegativity claim was refused for want of a wrap proof\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_unsigned_nonnegative_sum.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"ensure-unproven", "index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert set(reasons) == {"a_signed_sum_may_be_negative", "an_unguarded_difference_is_nonnegative", "a_nested_difference_is_nonnegative", "a_strict_claim_is_not_admitted", "a_wrapping_sum_bounds_nothing", "a_wrapping_sum_is_no_index", "an_exact_guard_bounds_its_own_sum"}; assert reasons["an_unguarded_difference_is_nonnegative"] == "verified"; assert reasons["an_exact_guard_bounds_its_own_sum"] == "verified"; assert reasons["a_nested_difference_is_nonnegative"] == "verified"; assert all(reasons[name] == "body-unverified" for name in ("a_signed_sum_may_be_negative", "a_strict_claim_is_not_admitted", "a_wrapping_sum_bounds_nothing", "a_wrapping_sum_is_no_index"))'
rejected_unsigned_nonnegative_sum_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_unsigned_nonnegative_sum_status" -ne 0 ]]; then
    printf 'proof test matrix failed: the nonnegativity rule admitted more than nonnegativity\n' >&2
    exit 1
fi

# A guard reaches the statements after it negated, and the order query read only the positive
# spelling, so the ordinary early-return range check was stated and unreadable. Complementarity is
# what the negation gives; transitivity and a modular comparison are not.
set +e
run_json_report "$ROOT_DIR/examples/negated_guard_range.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"a_negated_range_check", "the_same_check_as_a_condition", "two_places", "a_modular_guard_bounds_its_own_sum"}'
negated_guard_range_status=${PIPESTATUS[1]}
set -e
if [[ "$negated_guard_range_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a negated range check was unreadable\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_negated_guard_range.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; formation = [f for f in report["findings"] if f["kind"] == "contract-proposition-type"]; assert len(formation) == 6 and {f["name"] for f in formation} == {"a_negated_struct_order_does_not_chain", "a_negated_struct_order_gives_no_strict_chain"}; assert {f["kind"] for f in report["findings"]} == {"contract-proposition-type", "index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert set(reasons) == {"a_negated_struct_order_does_not_chain", "a_negated_struct_order_gives_no_strict_chain", "a_negated_modular_guard_bounds_nothing", "a_negated_equality_is_not_an_order"}; assert all(reason == "body-unverified" for reason in reasons.values())'
rejected_negated_guard_range_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_negated_guard_range_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a negated comparison gave more than its complement\n' >&2
    exit 1
fi

# A lend that cannot outlive its call leaves nothing a later call could reach, so a loop entered
# afterwards keeps the binding. It is still a write during its own call, and a callee that can keep
# it -- through a parameter or a return whose type can hold a reference -- keeps the old answer.
set +e
run_json_report "$ROOT_DIR/examples/confined_lend_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"fill", "read_only", "a_confined_lend_before_a_loop", "a_shared_lend_before_a_loop", "two_confined_lends"}'
confined_lend_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$confined_lend_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a lend that ends with its call still forgot a loop binding\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_confined_lend_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert report["summary"]["semantic_errors"] == 1; assert any(diagnostic["name"] == "holder" and "cannot be returned with a region-less type" in diagnostic["message"] for diagnostic in report["semantic_diagnostics"]); assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"borrow-call-summary-unsupported", "ensure-unproven", "index-upper-unproven"}; assert {(f["kind"], f["name"]) for f in report["findings"] if f["kind"] == "borrow-call-summary-unsupported"} == {("borrow-call-summary-unsupported", "a_leaked_lend_loses_the_extent"), ("borrow-call-summary-unsupported", "a_returned_lend_loses_it_too")}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_leaked_lend_loses_the_extent"] == "body-unverified"; assert reasons["a_returned_lend_loses_it_too"] == "body-unverified"; assert reasons["a_confined_lend_still_writes"] == "body-unverified"; assert reasons["a_lend_inside_the_loop"] == "body-unverified"'
rejected_confined_lend_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_confined_lend_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a lend that can outlive its call was treated as confined\n' >&2
    exit 1
fi

# The same question at the call inside the loop: an opaque call clears the state and restores what
# it could not have reached, and that restore asked the whole frame's aliased set. A lend that ends
# with its call is not part of this call's reach; a lend this call performs is.
set +e
run_json_report "$ROOT_DIR/examples/confined_lend_across_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"fill", "note", "a_call_in_the_body_keeps_the_range", "a_lent_local_in_the_body", "an_element_argument"}'
confined_lend_across_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$confined_lend_across_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call in a loop body lost a range fact it could not reach\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_confined_lend_across_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"borrow-call-summary-unsupported", "ensure-unproven", "index-upper-unproven"}; assert {(f["kind"], f["name"]) for f in report["findings"] if f["kind"] == "borrow-call-summary-unsupported"} == {("borrow-call-summary-unsupported", "an_escaping_lend_loses_the_range")}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["an_escaping_lend_loses_the_range"] == "body-unverified"; assert reasons["the_body_lends_the_collection"] == "body-unverified"; assert reasons["a_fact_before_the_lend"] == "body-unverified"'
rejected_confined_lend_across_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_confined_lend_across_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call kept a fact over a binding it could reach\n' >&2
    exit 1
fi

# An aggregate local kept its initializer as its value, so a call initializer made every place under
# it -- `values.count`, `located.node` -- a term with no place root, and an index into it was
# reported opaque rather than given an obligation. The symbol makes them places; it states nothing
# about the value, and every obligation the old spelling owed is still owed.
set +e
run_json_report "$ROOT_DIR/examples/aggregate_local_symbol.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"affine_of", "make", "a_container_local_from_a_call", "a_struct_local_from_a_call", "a_loop_over_a_call_local"}'
aggregate_local_symbol_status=${PIPESTATUS[1]}
set -e
if [[ "$aggregate_local_symbol_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a place under an aggregate local was not a place\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_aggregate_local_symbol.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"ensure-unproven", "index-bounds-opaque", "index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["an_unguarded_index_is_still_owed"] == "body-unverified"; assert reasons["a_guard_over_another_collection"] == "body-unverified"; assert reasons["a_field_is_not_a_claim"] == "body-unverified"; assert reasons["a_rebound_local_loses_its_guard"] == "body-unverified"'
rejected_aggregate_local_symbol_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_aggregate_local_symbol_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an aggregate local symbol claimed something about its value\n' >&2
    exit 1
fi

# A call reaches the caller's state only through references and globals, so a by-value scalar
# nothing in the body references keeps its recorded value across the call; at a branch join, a
# value every reaching arm still agrees on keeps it too. A referenced binding, a value recorded in
# terms of one, and a value an arm overwrote must all still be forgotten.
set +e
run_json_report "$ROOT_DIR/examples/call_boundary_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert not [goal for goal in report["goals"] if not goal["proven"]]; proven = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] == "goal"}; assert {"loop_binder_survives_a_declaration_call", "value_survives_a_declaration_call", "value_survives_an_assignment_call", "value_survives_a_statement_call", "loop_binder_survives_a_guarded_call", "value_survives_a_returning_branch"} <= proven; assert not report["findings"]'
call_boundary_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$call_boundary_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a binding no callee can reach did not survive the call boundary\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_call_boundary_binding.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {finding["name"] for finding in report["findings"] if finding["kind"] == "ensure-unproven"}; assert owners == {"referenced_value_must_not_survive", "value_over_a_referenced_binding_must_not_follow_it", "referenced_value_must_not_survive_a_statement_call", "value_overwritten_in_one_arm_must_not_survive", "value_overwritten_in_the_surviving_arm_must_not_survive"}; assert all(goal["proven"] for goal in report["goals"] if goal["rule"] != "goal")'
rejected_call_boundary_binding_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_call_boundary_binding_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a binding a callee or an arm can rewrite survived the boundary\n' >&2
    exit 1
fi

# An impure call on the right of `and`/`or` may not run. It is checked and havocked as if it ran,
# nothing only the run establishes survives, and the statement no longer invalidates its path.
set +e
run_json_report "$ROOT_DIR/examples/short_circuit_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["findings"] == []; assert all(goal["proven"] for goal in report["goals"]); verified = {declaration["name"] for declaration in report["declaration_details"] if declaration["kind"] == "function" and declaration["verified"]}; assert {"guard_with_a_skippable_call", "declaration_with_a_skippable_call", "return_with_a_skippable_call", "caller_of_the_returning_shape"} <= verified'
short_circuit_call_status=${PIPESTATUS[1]}
set -e
if [[ "$short_circuit_call_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a short-circuited impure call still invalidates its path\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_short_circuit_call.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; kinds = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert kinds == {("skipped_call_must_not_establish_and", "ensure-unproven"), ("skipped_call_must_not_establish_or", "ensure-unproven"), ("skipped_call_must_not_establish_a_guard", "ensure-unproven"), ("mutable_left_fact_must_not_survive", "ensure-unproven"), ("pre_call_value_must_not_survive", "ensure-unproven"), ("skipped_requires_is_still_checked", "call-requires-unproven")}; assert not any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); goals = {goal["name"]: goal["proven"] for goal in report["goals"] if goal["rule"] == "goal" and goal["name"] != "reset"}; assert goals and not any(goals.values())'
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
run_json_report "$ROOT_DIR/examples/branch_conjunct_placeholder.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; goals = [goal for goal in report["goals"] if goal["name"] == "conjunct_beside_a_placeholder" and goal["rule"] == "goal"]; assert goals and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in goals); assert any(origin["kind"] == "branch-condition" for goal in goals for origin in goal["fact_origins"]); assert not any(origin["kind"] == "branch-conjunct" for goal in goals for origin in goal["fact_origins"])'
branch_conjunct_placeholder_status=${PIPESTATUS[1]}
set -e
if [[ "$branch_conjunct_placeholder_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a conjunct beside a placeholder did not prove and replay\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_branch_conjunct_placeholder.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {goal["line"]: goal for goal in report["goals"] if goal["name"] == "placeholder_conjunct_must_not_become_a_fact" and goal["rule"] == "goal"}; assert goals and any(not goal["proven"] for goal in goals.values()); assert not any(origin["kind"] == "branch-conjunct" for goal in goals.values() for origin in goal["fact_origins"]); assert ("placeholder_conjunct_must_not_become_a_fact", "ensure-unproven") in {(finding["name"], finding["kind"]) for finding in report["findings"]}'
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
run_json_report "$ROOT_DIR/examples/loop_entry_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = [goal for goal in report["goals"] if goal["rule"] != "resource-safety"]; assert goals and all(goal["proven"] for goal in goals); names = {goal["name"] for goal in goals}; assert {"unwritten_binding_keeps_its_fact", "condition_bounds_the_body", "sound_invariant_is_preserved", "binder_range_survives"} <= names; assert sum(1 for goal in goals if goal["name"] == "sound_invariant_is_preserved") == 2; kinds = {finding["kind"] for finding in report["findings"]}; assert kinds == {"loop-invariant-missing"}'
loop_entry_state_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_entry_state_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop body lost a fact that holds on every iteration\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/while_loop_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = [goal for goal in report["goals"] if goal["rule"] != "resource-safety"]; assert goals and all(goal["proven"] for goal in goals); assert {"source_times", "pushed_times"} <= {goal["name"] for goal in goals}; assert report["findings"] == []'
while_loop_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$while_loop_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a while loop dropped a guard or a fact over a binding it does not write (G75)\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_while_loop_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert ("written_binding_loses_its_fact_after_the_loop", "call-requires-unproven") in owners; assert ("written_binding_loses_its_fact_in_the_body", "call-requires-unproven") in owners; assert ("pushed_collection_still_grows", "call-requires-unproven") in owners'
rejected_while_loop_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_while_loop_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fact over a binding the while body writes survived the loop (G75)\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_loop_entry_state.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {}; [goals.setdefault(goal["name"], []).append(goal["proven"]) for goal in report["goals"] if goal["rule"] == "goal"]; assert goals["entry_value_must_not_reach_the_body"] == [False]; assert goals["entry_value_must_not_reach_an_uncaptured_body"] == [False]; assert False in goals["false_invariant_must_not_be_preserved"]; assert not all(goals["break_must_not_yield_the_exit_condition"]); owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert ("entry_value_must_not_reach_the_body", "call-requires-unproven") in owners; assert ("entry_value_must_not_reach_an_uncaptured_body", "call-requires-unproven") in owners; assert ("false_invariant_must_not_be_preserved", "invariant-not-preserved") in owners; assert ("break_must_not_yield_the_exit_condition", "ensure-unproven") in owners'
rejected_loop_entry_state_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_entry_state_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop body used the entry value of a binding it rewrites\n' >&2
    exit 1
fi

# An invariant-less loop still runs its body only when the condition holds, and a shared borrow's
# element count is stable across a call. Together these discharge the dominant loop shape here.
set +e
run_json_report "$ROOT_DIR/examples/loop_condition_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; proven = {(goal["name"], goal["rule"]) for goal in report["goals"] if goal["proven"]}; assert ("while_condition_bounds_the_body", "index-upper") in proven; assert ("shared_extent_survives_a_call_in_the_body", "index-upper") in proven; assert ("shared_extent_survives_a_call", "index-upper") in proven; kinds = {finding["kind"] for finding in report["findings"]}; assert kinds == {"loop-invariant-missing"}'
loop_condition_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_condition_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop condition or a shared extent did not reach the body\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_loop_condition_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("unrelated_condition_proves_no_bound", "index-upper")] is False; assert goals[("mutable_extent_must_not_survive_a_call", "index-upper")] is False; assert goals[("entry_value_must_not_reach_the_body", "goal")] is False; assert any(f["kind"] == "call-requires-unproven" for f in report["findings"])'
rejected_loop_condition_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_condition_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop condition or a mutable extent claimed too much\n' >&2
    exit 1
fi

# A mutable global is the one path a shared borrow does not exclude, so the extent rule is
# withdrawn from any program that declares one.
set +e
run_json_report "$ROOT_DIR/examples/rejected_shared_extent_global.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("borrowed_extent_must_not_survive", "index-upper")] is False'
rejected_shared_extent_global_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_shared_extent_global_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a shared extent survived a mutable global write\n' >&2
    exit 1
fi

# Structural transitivity reaches goals the difference engine cannot name, and reaches nothing
# built out of a user comparison.
set +e
run_json_report "$ROOT_DIR/examples/comparison_chain.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["verification_state"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["findings"] == []; assert report["trust"]["trusted_assumptions"] == []'
comparison_chain_status=${PIPESTATUS[1]}
set -e
if [[ "$comparison_chain_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a comparison chain did not reach an unnameable bound\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_comparison_chain.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["obligations"] == 10; assert report["replay"]["certificates"] == report["replay"]["replayed"] == 2; assert report["replay"]["gaps"] == 0; formations = [finding for finding in report["findings"] if finding["kind"] == "contract-proposition-type"]; assert len(formations) == 6; assert {finding["name"] for finding in formations} == {"struct_order_is_not_transitive", "struct_non_strict_order_is_not_transitive"}; assert {finding["line"] for finding in formations} == {8, 9, 10, 14, 15, 16}; goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}; assert goals[("non_strict_chain_gives_no_strict_goal", "goal")] is False; assert goals[("wrong_direction_chain", "goal")] is False; declarations = {decl["name"]: decl for decl in report["declaration_details"] if decl["kind"] == "function"}; assert all(not declarations[name]["verified"] and declarations[name]["verification_reason"] == "body-unverified" for name in ("struct_order_is_not_transitive", "struct_non_strict_order_is_not_transitive"))'
rejected_comparison_chain_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_comparison_chain_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a comparison chain claimed a user comparison or a direction it does not have\n' >&2
    exit 1
fi

# A callee whose only findings widen its own state still exports its summary, and says so.
set +e
run_json_report "$ROOT_DIR/examples/widened_state_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; kinds = {f["kind"] for f in report["findings"]}; assert kinds == {"loop-invariant-missing"}; assert not [g for g in report["goals"] if not g["proven"]]; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert ("caller_may_use_that_summary", "goal") in proven; assert ("caller_may_use_that_one_too", "goal") in proven; assert ("two_levels_above", "goal") in proven; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["loop_is_havocked_but_the_contract_holds"] == "verified"; assert reasons["caller_may_use_that_summary"] == "verified"; assert reasons["missing_invariant_is_havocked_too"] == "contract-verified-widened-state"; assert reasons["caller_may_use_that_one_too"] == "contract-verified-widened-state"; assert reasons["two_levels_above"] == "contract-verified-widened-state"; assert reasons["untouched_leaf"] == "verified"; assert reasons["untouched_caller"] == "verified"'
widened_state_summary_status=${PIPESTATUS[1]}
set -e
if [[ "$widened_state_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a widened-state contract did not export its summary, or did not say so\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_widened_state_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(f["name"], f["kind"]) for f in report["findings"]}; assert ("caller_gets_no_summary", "function-summary-unverified") in owners; assert ("caller_gets_no_summary_from_an_unproven_index", "function-summary-unverified") in owners; assert ("writes_outside_its_frame", "frame-write-outside") in owners; assert ("caller_gets_no_frame", "function-summary-unverified") in owners; assert ("breaks_what_it_preserves", "frame-preserve-write") in owners; assert ("caller_must_lose_the_fact", "ensure-unproven") in owners; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; usable = ("verified", "contract-verified-widened-state"); assert reasons["unproven_ensure_with_a_loop"] not in usable; assert reasons["unproven_index"] not in usable; assert reasons["writes_outside_its_frame"] not in usable; assert reasons["breaks_what_it_preserves"] not in usable; assert reasons["unframed_widened"] == "contract-verified-widened-state"; assert reasons["caller_must_lose_the_fact"] not in usable'
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
run_json_report "$ROOT_DIR/examples/rejected_condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; unsupported = {name for kind, name in findings if kind == "expression-unsupported"}; assert {"conditional_call", "literal_field_call"} <= unsupported; assert "right_of_and" not in unsupported; assert "right_of_or" not in unsupported; assert ("index-upper-unproven", "bound_after_guard") in findings; assert ("index-upper-unproven", "stored_before_guard") in findings; assert not any(goal["proven"] and goal["rule"] == "index-upper" for goal in report["goals"])'
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
proved_goal=$(run_json_report "$ROOT_DIR/examples/condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); print(next(index for index, goal in enumerate(report["goals"]) if goal["rule"] == "index-upper" and goal["proven"]))')
"$ROOT_DIR/build/elisa-proof" --proof "$proved_goal" "$ROOT_DIR/examples/condition_call_positions.elisa" > "$proof_render_dir/proved.txt"
proof_render_proved_status=$?
open_goal=$(run_json_report "$ROOT_DIR/examples/rejected_condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); print(next(index for index, goal in enumerate(report["goals"]) if not goal["proven"]))')
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
