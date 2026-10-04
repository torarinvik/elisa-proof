# shellcheck shell=bash
# Part 7 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
if [[ "$rejected_converted_index_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a converted index was admitted without its bounds\n' >&2
    exit 1
fi

# An index in an if-expression arm is bounds-checked under that arm's condition.
set +e
run_json_report "$ROOT_DIR/examples/guarded_arm_indexes.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
guarded_arm_index_status=${PIPESTATUS[1]}
set -e
if [[ "$guarded_arm_index_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a guarded index in a conditional arm was not proven\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_guarded_arm_indexes.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert ("other_guard", "index-upper-unproven") in owners; assert ("else_arm", "index-upper-unproven") in owners'
rejected_guarded_arm_index_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_guarded_arm_index_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a conditional arm index was admitted under the wrong guard\n' >&2
    exit 1
fi

# The then arm of an if-expression is range-checked under its own condition.
set +e
run_json_report "$ROOT_DIR/examples/guarded_conditional_arms.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
guarded_conditional_arms_status=${PIPESTATUS[1]}
set -e
if [[ "$guarded_conditional_arms_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a subtraction guarded by its if-expression condition was refused\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_guarded_conditional_arms.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("wrong_arm", "ensure-unproven"), ("weak_guard", "ensure-unproven")}'
rejected_guarded_conditional_arms_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_guarded_conditional_arms_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an if-expression condition guarded the wrong arm or more than it says\n' >&2
    exit 1
fi

# A closed constant beside a strictly typed peer is read at the peers width.
set +e
run_json_report "$ROOT_DIR/examples/typed_wide_constants.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
typed_wide_constants_status=${PIPESTATUS[1]}
set -e
if [[ "$typed_wide_constants_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a wide, folded or conditional constant beside a typed peer lost its bound\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_typed_wide_constants.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("wrapped_bound", "ensure-unproven"), ("off_by_one", "ensure-unproven"), ("wide_then_arm", "ensure-unproven")}'
rejected_typed_wide_constants_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_typed_wide_constants_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a constant typed at its peer width hid a wrap or a wrong bound\n' >&2
    exit 1
fi

# The else arm of an if-expression is range-checked under the complement of its condition.
set +e
run_json_report "$ROOT_DIR/examples/complemented_else_arms.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
complemented_else_arms_status=${PIPESTATUS[1]}
set -e
if [[ "$complemented_else_arms_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an else arm guarded by the failed condition was refused\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_complemented_else_arms.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("wrong_complement", "ensure-unproven"), ("then_arm_unguarded", "ensure-unproven"), ("weak_complement", "ensure-unproven"), ("conjunction_complement", "ensure-unproven")}'
rejected_complemented_else_arms_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_complemented_else_arms_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a complement guarded the wrong arm or more than it says\n' >&2
    exit 1
fi

# A block-form captured loop keeps the invariants it checked after it.
set +e
run_json_report "$ROOT_DIR/examples/captured_block_exit.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
captured_block_exit_status=${PIPESTATUS[1]}
set -e
if [[ "$captured_block_exit_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a block-form captured loop lost its invariants after the loop\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_captured_block_exit.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert owners == {("unchecked", "ensure-unproven"), ("broken", "invariant-not-preserved"), ("broken", "ensure-unproven")}'
rejected_captured_block_exit_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_captured_block_exit_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a captured loop kept a fact it never checked or broke\n' >&2
    exit 1
fi

# A global constant named only in a tail accumulator loop's invariant is imported, and its
# value fact survives the clears at the loop boundary.
set +e
run_json_report "$ROOT_DIR/examples/global_constant_loop_exit.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]'
global_constant_loop_exit_status=${PIPESTATUS[1]}
set -e
if [[ "$global_constant_loop_exit_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a global constant in a tail-loop invariant was not imported\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_global_constant_loop_exit.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("last_slot", "ensure-unproven")} <= owners'
rejected_global_constant_loop_exit_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_global_constant_loop_exit_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a tail-loop exit proved a bound tighter than its constant\n' >&2
    exit 1
fi

# A fact both arms of an if establish over the names they rebind survives the join as a
# re-proved `branch-join` fact. A fact only one arm proves, or one about a value rebound from
# itself (`b <- b + 1`), does not.
set +e
run_json_report "$ROOT_DIR/examples/branch_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}; assert "branch-join" in origins'
branch_join_status=${PIPESTATUS[1]}
set -e
if [[ "$branch_join_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fact both arms establish over a rebound name was lost at the join\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_branch_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; owners = {(finding["name"], finding["kind"]) for finding in report["findings"]}; assert {("not_always_kept", "ensure-unproven"), ("replace_too_far", "ensure-unproven"), ("stale_rebind", "ensure-unproven")} <= owners'
rejected_branch_join_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_branch_join_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a join kept a fact only one arm establishes, or one about a stale value\n' >&2
    exit 1
fi

# A difference constraint carries an interval to the name the overflow guard asks about.
set +e
run_json_report "$ROOT_DIR/examples/bound_propagation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert all((owner, "goal") in proven for owner in ("increment_under_a_bounded_limit", "increment_through_a_chain", "lower_bound_travels", "unsigned_increment_under_a_strict_peer", "unsigned_increment_under_a_reversed_peer", "strict_fact_needs_no_upper_bound", "strict_fact_needs_no_related_bound"))'
bound_propagation_status=${PIPESTATUS[1]}
set -e
if [[ "$bound_propagation_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a derivable interval did not reach the overflow guard\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_bound_propagation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(g["name"], g["rule"]): g["proven"] for g in report["goals"]}; refused = ("unsigned_step_of_two", "unsigned_increment_under_a_non_strict_peer", "unsigned_peer_of_another_name", "non_strict_premise_is_not_shiftable"); assert all(goals[(owner, "goal")] is False for owner in refused); assert {f["kind"] for f in report["findings"]} == {"ensure-unproven"}'
rejected_bound_propagation_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_bound_propagation_status" -ne 0 ]]; then
    printf 'proof test matrix failed: propagation invented an interval\n' >&2
    exit 1
fi

# `a < R` gives `a + 1 <= R` for any term R, matched structurally so a field place is reachable.
set +e
run_json_report "$ROOT_DIR/examples/strict_shift.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert all((owner, "goal") in proven for owner in ("shift_to_a_field", "shift_to_a_name", "shift_from_a_reversed_fact", "shift_to_a_collection_extent"))'
strict_shift_status=${PIPESTATUS[1]}
set -e
if [[ "$strict_shift_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a strict fact did not shift to its own bound\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_strict_shift.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(g["name"], g["rule"]): g["proven"] for g in report["goals"]}; refused = ("needs_a_strict_fact", "gives_no_strict_conclusion", "moves_by_one_only", "bounds_another_term", "another_collection_extent"); assert all(goals[(owner, "goal")] is False for owner in refused); assert {f["kind"] for f in report["findings"]} == {"ensure-unproven"}'
rejected_strict_shift_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_strict_shift_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a shift was taken where none follows\n' >&2
    exit 1
fi

# A sum of two non-constant terms is bounded by the term its guarded subtraction names.
set +e
run_json_report "$ROOT_DIR/examples/sum_bound.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert all((owner, "goal") in proven for owner in ("transpose_the_subtraction", "a_term_under_the_bound", "the_same_for_a_signed_sum", "commuted"))'
sum_bound_status=${PIPESTATUS[1]}
set -e
if [[ "$sum_bound_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a guarded subtraction did not bound its own sum\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_signed_sum_wrap.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(g["name"], g["rule"]): g["proven"] for g in report["goals"]}; assert goals[("negative_count_can_wrap_above_bound", "resource-safety")] is True; assert goals[("negative_count_can_wrap_above_bound", "goal")] is False; assert {finding["kind"] for finding in report["findings"]} == {"ensure-unproven"}'
rejected_signed_sum_wrap_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_signed_sum_wrap_status" -ne 0 ]]; then
    printf 'proof test matrix failed: signed sum overflow escaped the guarded-sum rule\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_sum_bound.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(g["name"], g["rule"]): g["proven"] for g in report["goals"]}; refused = ("a_modular_premise_is_not_a_bound", "the_subtraction_needs_its_guard", "a_non_strict_step_gives_no_strict_goal", "a_bound_on_another_term"); assert all(goals[(owner, "goal")] is False for owner in refused); assert {f["kind"] for f in report["findings"]} == {"ensure-unproven"}'
rejected_sum_bound_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_sum_bound_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a wrapped sum was read as an integer bound\n' >&2
    exit 1
fi

# `or` and `and` short-circuit, so an operand the left one settles owes no range argument.
set +e
run_json_report "$ROOT_DIR/examples/settled_operand.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert all((owner, "goal") in proven for owner in ("empty_range_is_valid", "a_settled_conjunct", "the_live_operand_is_still_owed"))'
settled_operand_status=${PIPESTATUS[1]}
set -e
if [[ "$settled_operand_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unreachable operand was still charged for its range\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_settled_operand.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(g["name"], g["rule"]): g["proven"] for g in report["goals"]}; refused = ("or_left_false_still_owes_the_right", "and_left_true_still_owes_the_right", "a_settled_operand_does_not_settle_a_sibling", "an_unsettled_left_keeps_the_gate"); assert all(goals[(owner, "goal")] is False for owner in refused); assert {f["kind"] for f in report["findings"]} == {"ensure-unproven"}'
rejected_settled_operand_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_settled_operand_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a live operand was settled by its neighbour\n' >&2
    exit 1
fi

# An early return leaves its condition negated, and a negated comparison between two atoms is an
# order between the same two atoms.
set +e
run_json_report "$ROOT_DIR/examples/negated_guard_order.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; proven = {(g["name"], g["rule"]) for g in report["goals"] if g["proven"]}; assert all((owner, "goal") in proven for owner in ("a_guard_reaches_past_its_own_return", "a_guard_inside_a_disjunction_still_reaches", "a_bounded_sum_follows_from_the_pair"))'
negated_guard_status=${PIPESTATUS[1]}
set -e
if [[ "$negated_guard_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a negated guard did not reach past its own return\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_negated_guard_order.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; goals = {(g["name"], g["rule"]): g["proven"] for g in report["goals"]}; refused = ("a_negation_of_the_wrong_order", "an_inequality_is_not_an_order", "a_guard_on_another_pair", "the_bound_the_guards_give_is_not_strict"); assert all(goals[(owner, "goal")] is False for owner in refused); assert {f["kind"] for f in report["findings"]} == {"ensure-unproven"}'
rejected_negated_guard_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_negated_guard_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a negated guard said more than it says\n' >&2
    exit 1
fi

# An order between two places guards its own subtraction; a conjunction is read as its conjuncts;
# a proposition beside its negation closes the branch a disjunctive premise refutes; and an
# unsigned expression certified not to wrap is nonnegative.
set +e
run_json_report "$ROOT_DIR/examples/place_order.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"a_place_guards_its_own_subtraction", "a_conjunction_is_read_as_its_conjuncts", "a_denied_disjunct_leaves_the_other", "a_guarded_difference_is_nonnegative", "a_callee_range_check", "a_summary_the_caller_guarded_on"}'
place_order_status=${PIPESTATUS[1]}
set -e
if [[ "$place_order_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a guard stated between two places was unreadable\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_place_order.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; refused = ("a_place_order_in_the_wrong_direction", "a_place_order_on_another_pair", "a_disjunct_is_not_a_conjunct", "a_negation_denies_only_itself", "nonnegative_is_not_positive", "an_unguarded_summary_asserts_nothing"); assert all(reasons[owner] == "body-unverified" for owner in refused)'
rejected_place_order_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_place_order_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fact list was read for more than it states\n' >&2
    exit 1
fi

# An unsigned machine value is nonnegative whatever it holds, and a field's type says so through a
# marker over the place, which the general width function never sees.
set +e
run_json_report "$ROOT_DIR/examples/unsigned_place.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"range_valid", "a_guarded_range_over_a_field", "a_field_is_nonnegative", "an_unguarded_difference_is_still_nonnegative", "a_qualified_struct_field_is_nonnegative"}'
unsigned_place_status=${PIPESTATUS[1]}
set -e
if [[ "$unsigned_place_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unsigned field was not known to be nonnegative\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_unsigned_place.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; refused = ("a_signed_field_is_not_nonnegative", "a_field_is_not_positive", "a_call_result_carries_no_marker", "an_unsigned_field_has_no_upper_bound", "an_ambiguous_leaf_names_no_struct"); assert all(reasons[owner] == "body-unverified" for owner in refused)'
rejected_unsigned_place_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_unsigned_place_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a place marker answered a question it does not\n' >&2
    exit 1
fi

# An empty literal is empty. The term is the value, so nothing can alias it or make its count
# something else, and a length invariant starts from exactly this.
set +e
run_json_report "$ROOT_DIR/examples/literal_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"an_empty_literal_is_empty", "a_length_invariant_starts_at_zero"}'
literal_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$literal_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an empty literal was not known to be empty\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_literal_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; refused = ("a_push_is_not_modelled", "a_parameter_has_no_literal", "a_field_named_count_is_not_a_length", "a_literal_length_is_not_an_element_bound", "a_non_empty_literal_length_is_not_read", "a_short_literal_has_its_own_length_only"); assert all(reasons[owner] == "body-unverified" for owner in refused)'
rejected_literal_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_literal_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a literal length was read where there is no literal\n' >&2
    exit 1
fi

# A collection a local owns outright is a binding no callee can name, so its extent survives a call
# the way a by-value scalar does. Everything a callee can reach loses it.
set +e
run_json_report "$ROOT_DIR/examples/owned_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"grow", "an_owned_extent_survives_a_call_that_cannot_reach_it", "an_owned_extent_survives_another_collection_being_grown"}'
owned_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$owned_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an owned extent did not survive an unreachable call\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_owned_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; refused = ("a_lent_local_loses_its_extent", "a_reference_local_owns_nothing", "a_push_gives_no_new_length", "a_shared_argument_still_loses_the_extent"); assert all(reasons[owner] == "body-unverified" for owner in refused)'
rejected_owned_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_owned_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an extent was kept for a collection a callee can reach\n' >&2
    exit 1
fi

# A capture list is not evidence of a write. A capture the body only reads keeps its facts; one the
# body assigns, or hands to something that can write it, does not.
set +e
run_json_report "$ROOT_DIR/examples/captured_scalar.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"needs_bound", "touch", "a_read_only_capture_keeps_its_precondition", "a_read_only_capture_survives_a_mutating_body"}'
captured_scalar_status=${PIPESTATUS[1]}
set -e
if [[ "$captured_scalar_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a capture the body only reads lost its facts\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_captured_scalar.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; refused = ("a_capture_the_body_assigns_is_forgotten", "a_capture_handed_to_a_writer_is_forgotten", "an_uncaptured_binding_the_body_assigns_is_forgotten"); assert all(reasons[owner] == "body-unverified" for owner in refused)'
rejected_captured_scalar_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_captured_scalar_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a binding a captured body writes kept its facts\n' >&2
    exit 1
fi

# A loop-header accumulator is the one binding its loop may write, and a loop whose value is the
# accumulator is checked statement by statement before that value is returned.
set +e
run_json_report "$ROOT_DIR/examples/loop_accumulator.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"count_small", "first_small", "bounded_total"}'
loop_accumulator_status=${PIPESTATUS[1]}
set -e
if [[ "$loop_accumulator_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a loop-header accumulator loop was refused\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_loop_accumulator.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert all(reason == "body-unverified" for reason in reasons.values()) and len(reasons) == 3; kinds = {(f["name"], f["kind"]) for f in report["findings"]}; assert ("an_accumulator_body_still_checks_its_index", "index-upper-unproven") in kinds; assert ("an_accumulator_value_keeps_its_ensure", "ensure-unproven") in kinds; assert ("an_ordinary_local_stays_immutable", "resource-write-readonly") in kinds'
rejected_loop_accumulator_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_loop_accumulator_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an accumulator loop skipped a check or widened the write exemption\n' >&2
    exit 1
fi

# `pass` is indistinguishable at this AST layer from a construct the frontend dropped, so it is
# refused and the refusal havocs everything after it. A match whose arms agree is one condition.
set +e
run_json_report "$ROOT_DIR/examples/no_op_statement.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"needs_bound", "a_condition_keeps_the_state", "every_arm_returning_keeps_it_too", "a_pass_arm_keeps_the_state"}'
no_op_statement_status=${PIPESTATUS[1]}
set -e
if [[ "$no_op_statement_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a match whose arms agree lost the state before it\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_no_op_statement.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert {f["kind"] for f in report["findings"]} == {"expression-unsupported", "call-requires-unproven"}; assert sum(f["kind"] == "expression-unsupported" for f in report["findings"]) == 2; assert any(f["kind"] == "call-requires-unproven" and f["name"] == "the_refusal_reaches_past_the_match" for f in report["findings"]); reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_dropped_arm_is_refused"] == "body-unverified"; assert reasons["the_refusal_reaches_past_the_match"] == "body-unverified"'
rejected_no_op_statement_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_no_op_statement_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unreadable statement was admitted\n' >&2
    exit 1
fi

# A call is modelled at a statement boundary. Buried in a larger value expression it has none, so
# it is refused; bound to a local first it is the same program where the checker can model it.
set +e
run_json_report "$ROOT_DIR/examples/nested_call_value.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"emit", "a_call_may_be_the_whole_value", "a_call_bound_first_is_modelled", "the_binding_keeps_the_state_after_it", "a_call_bound_before_a_conditional_is_modelled"}'
nested_call_value_status=${PIPESTATUS[1]}
set -e
if [[ "$nested_call_value_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call bound to a local was not modelled\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_nested_call_value.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert {f["kind"] for f in report["findings"]} == {"expression-unsupported"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_call_nested_in_a_tuple_is_refused"] == "body-unverified"; assert reasons["the_refusal_reaches_past_the_statement"] == "body-unverified"; assert reasons["a_call_inside_a_conditional_is_refused"] == "body-unverified"'
rejected_nested_call_value_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_nested_call_value_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call with no statement boundary was admitted\n' >&2
    exit 1
fi

# A collection builtin writes its receiver and reads its arguments. Recording that write is what
# gives the borrow rules their say over it.
set +e
run_json_report "$ROOT_DIR/examples/collection_builtin.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"read", "a_push_is_a_write_to_its_receiver", "a_copy_clears_and_extends", "a_borrow_taken_after_the_write_is_fine", "a_truncate_is_a_write", "a_conversion_has_no_receiver_to_write"}'
collection_builtin_status=${PIPESTATUS[1]}
set -e
if [[ "$collection_builtin_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a collection builtin was not recorded as a write\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_collection_builtin.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 2; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"borrow-write-conflict", "borrow-call-opaque"}; diagnostics = report["semantic_diagnostics"]; assert len(diagnostics) == 2 and {d["kind_code"] for d in diagnostics} == {393, 366}; assert all(d["line"] == 20 and d["severity"] == 1 for d in diagnostics); assert any(d["kind_code"] == 393 and d["name"] == "push" and "growing non-local storage" in d["message"] for d in diagnostics); assert any(d["kind_code"] == 366 and "stored into longer-lived region" in d["message"] for d in diagnostics); reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_push_while_a_borrow_is_live"] == "body-unverified"; assert reasons["a_region_argument_withdraws_the_admission"] == "body-unverified"; assert reasons["an_unmodelled_builtin_is_refused"] == "body-unverified"'
rejected_collection_builtin_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_collection_builtin_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a builtin write escaped the borrow rules\n' >&2
    exit 1
fi

# A declared function with the same leaf as a collection method must withdraw the builtin
# shortcut. Method-shaped AST nodes have no callable leaf, so this protects the receiver from an
# incomplete effect model for a user-defined UFCS call.
set +e
run_json_report "$ROOT_DIR/examples/rejected_shadowed_collection_builtin.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert any(f["kind"] == "borrow-call-opaque" and f["name"] == "shadowed_push_must_not_be_verified" for f in report["findings"]); reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["shadowed_push_must_not_be_verified"] == "body-unverified"'
rejected_shadowed_collection_builtin_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_shadowed_collection_builtin_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a declared collection-method name was admitted as a builtin\n' >&2
    exit 1
fi

# A call in a loop condition has no statement boundary either, and an opaque condition leaves the
# loop with no post-state claim at all. Binding the call before the loop keeps the condition.
set +e
# A conditional join must not overclaim: one arm leaves the bound false, and a condition
# that reads a rebound binding cannot vouch for the value after the branch (G75).
run_json_report "$ROOT_DIR/examples/rejected_conditional_join.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["replay"]["gaps"] == 0; assert report["summary"]["proven"] < report["summary"]["obligations"]; assert sorted((f["kind"], f["line"]) for f in report["findings"]) == [("ensure-unproven", 14), ("ensure-unproven", 25)]'
rejected_conditional_join_status=${PIPESTATUS[1]}
if [[ "$rejected_conditional_join_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a conditional join proved a false bound\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/bound_loop_condition.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"loop-invariant-missing"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_bound_limit_leaves_the_condition_readable"] == "contract-verified-widened-state"'
bound_loop_condition_status=${PIPESTATUS[1]}
set -e
if [[ "$bound_loop_condition_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a bound loop condition was still opaque\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_bound_loop_condition.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"loop-condition-opaque", "loop-invariant-missing"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_call_in_the_condition_is_opaque"] == "body-unverified"'
rejected_bound_loop_condition_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_bound_loop_condition_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a call in a loop condition was read as a condition\n' >&2
    exit 1
fi

# A block statement discards its own value and nothing else, and a collection's length is a scalar
# copy that hands a callee no capability over the collection.
set +e
run_json_report "$ROOT_DIR/examples/block_statement_region.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"fits", "a_captured_loop_over_a_region_binding", "an_extent_argument_is_a_scalar"}'
block_statement_region_status=${PIPESTATUS[1]}
set -e
if [[ "$block_statement_region_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a captured loop was read as a discarded region value\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_block_statement_region.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"region-expression-unsupported"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_discarded_region_value_is_refused"] == "body-unverified"; assert reasons["parentheses_do_not_hide_it"] == "body-unverified"'
rejected_block_statement_region_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_block_statement_region_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a discarded region value was admitted\n' >&2
    exit 1
fi

# A loop invariant cannot appear in a compiled source of this project, so a loop whose index bound
# needs one must be written not to need it. A forward scan keeping the last match is that rewrite.
set +e
run_json_report "$ROOT_DIR/examples/forward_scan.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"a_forward_scan_keeps_the_last_match", "an_existence_check_does_not_depend_on_order"}'
forward_scan_status=${PIPESTATUS[1]}
set -e
if [[ "$forward_scan_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a forward scan did not carry its own index bound\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_forward_scan.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"index-upper-unproven", "loop-invariant-missing"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_downward_scan_needs_an_invariant"] == "body-unverified"'
rejected_forward_scan_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_forward_scan_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a downward scan was given a bound it never states\n' >&2
    exit 1
fi

# The extent a loop range is written against may be nested. A root the body writes only elements
# under keeps every count under it; a whole write to a field keeps none.
set +e
run_json_report "$ROOT_DIR/examples/nested_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"a_loop_over_one_field_writing_another", "the_guard_may_come_first"}'
nested_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$nested_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a nested extent was lost to an element write beside it\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_nested_extent.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_whole_field_write_loses_every_extent"] == "body-unverified"'
rejected_nested_extent_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_nested_extent_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a whole field write kept an extent under its root\n' >&2
    exit 1
fi

# A binding that holds its value is this frame's storage, so a callee has no path to its fields
# either. A binding that holds a reference does not own what it names.
set +e
run_json_report "$ROOT_DIR/examples/value_root_field.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"grow", "a_field_of_a_value_parameter_survives_a_call", "a_second_field_survives_it_too"}'
value_root_field_status=${PIPESTATUS[1]}
set -e
if [[ "$value_root_field_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a field of a value binding was lost to a call\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_value_root_field.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"ensure-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_field_of_a_mutable_reference_does_not_survive"] == "body-unverified"; assert reasons["a_field_of_a_shared_reference_does_not_either"] == "body-unverified"'
rejected_value_root_field_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_value_root_field_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a field of a reference was kept across a call\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/implicit_shared_borrow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["findings"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"read", "read_value"}'
implicit_shared_borrow_status=${PIPESTATUS[1]}
set -e
if [[ "$implicit_shared_borrow_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an implicit shared borrow was not replayed as a capability\n' >&2
    exit 1
fi

# A shared borrow's extent is fixed for the borrow's lifetime, so a loop cannot change it and the
# guard taken over `name.count` still holds on every iteration. Lending the collection anywhere in
# the frame used to purge that guard at loop entry. Every other way the guarded quantity can move
# -- a mutable borrow, a rewritten scalar argument -- must still lose it.
set +e
run_json_report "$ROOT_DIR/examples/shared_extent_loop.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert not report["findings"]; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; verified = {d["name"] for d in report["declaration_details"] if d["kind"] == "function" and d["verification_reason"] == "verified"}; assert verified == {"range_valid", "reads", "a_shared_borrow_keeps_its_extent", "a_later_lend_does_not_reach_backwards", "a_lend_inside_the_loop"}'
shared_extent_loop_status=${PIPESTATUS[1]}
set -e
if [[ "$shared_extent_loop_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a shared borrow lost its extent at loop entry\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_shared_extent_loop.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_mutable_borrow_loses_its_extent"] == "body-unverified"; assert reasons["a_lent_mutable_borrow_loses_it_too"] == "body-unverified"; assert reasons["a_rewritten_argument_loses_the_guard"] == "body-unverified"'
rejected_shared_extent_loop_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_shared_extent_loop_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a moving extent or argument kept its guard at loop entry\n' >&2
    exit 1
fi

# A local bound to a collection literal records its facts over that literal. The replay driver's
# expression equality had no arm for one, so such a fact never matched its own trace and every
# certificate carrying it gapped. Exact, elementwise: a different literal is a different fact.
set +e
run_json_report "$ROOT_DIR/examples/replay_literal_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; lower = [g for g in report["goals"] if g["rule"] == "index-lower"]; assert len(lower) == 5; assert all(g["proven"] and g["replay_status"] == "replayed" for g in lower); assert report["status"] == "proved"; assert report["findings"] == []'
replay_literal_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$replay_literal_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fact over a collection literal did not replay\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_replay_literal_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["trust"]["trusted_assumptions"] == []; assert {f["kind"] for f in report["findings"]} == {"index-upper-unproven"}; reasons = {d["name"]: d["verification_reason"] for d in report["declaration_details"] if d["kind"] == "function"}; assert reasons["a_rebound_literal_loses_its_guard"] == "body-unverified"; assert reasons["a_guard_for_one_literal_is_not_a_guard_for_another"] == "body-unverified"; assert reasons["an_empty_literal_has_no_element"] == "body-unverified"'
rejected_replay_literal_facts_status=${PIPESTATUS[1]}
set -e
