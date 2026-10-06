# shellcheck shell=bash
# Part 2 of scripts/dogfood.sh; sourced in order by it, never run alone.
run_probe rejected_float_reflexivity examples/rejected_float_reflexivity.elisa 1
run_probe rejected_float_alias examples/rejected_float_alias.elisa 1
run_probe rejected_float_field examples/rejected_float_field.elisa 1
run_probe rejected_float_enum examples/rejected_float_enum.elisa 1
run_probe rejected_float_expression examples/rejected_float_expression.elisa 1
run_probe nullable_reference_comparison examples/nullable_reference_comparison.elisa 0
run_probe rejected_nonnullable_reference_null examples/rejected_nonnullable_reference_null.elisa 1
run_probe nullable_opaque_reference_comparison examples/nullable_opaque_reference_comparison.elisa 0
run_probe rejected_opaque_reference_ordering examples/rejected_opaque_reference_ordering.elisa 1
run_probe float_opaque_guard examples/float_opaque_guard.elisa 0
run_probe float_boolean_guard examples/float_boolean_guard.elisa 0
run_probe float_literal_guard examples/float_literal_guard.elisa 0
run_probe rejected_float_arithmetic_atom examples/rejected_float_arithmetic_atom.elisa 1
run_probe rejected_float_order_totality examples/rejected_float_order_totality.elisa 1
run_probe rejected_float_boolean_stale_fact examples/rejected_float_boolean_stale_fact.elisa 1
run_probe rejected_float_literal_stale_fact examples/rejected_float_literal_stale_fact.elisa 1
run_probe rejected_float_boolean_overloaded examples/rejected_float_boolean_overloaded.elisa 1
run_probe rejected_float_le_guard examples/rejected_float_le_guard.elisa 1
run_probe rejected_float_nan_order examples/rejected_float_nan_order.elisa 1
run_probe integer_alias examples/integer_alias.elisa 0
run_probe unsigned_alias examples/unsigned_alias.elisa 0
run_probe rejected_unsigned_alias examples/rejected_unsigned_alias.elisa 1
run_probe unsigned_refinement examples/unsigned_refinement.elisa 0
run_probe rejected_unsigned_refinement examples/rejected_unsigned_refinement.elisa 1
run_probe refinement_alias_contracts examples/refinement_alias_contracts.elisa 0
run_probe rejected_refinement_alias_argument examples/rejected_refinement_alias_argument.elisa 1
run_probe unsigned_fact_safety examples/unsigned_fact_safety.elisa 0
run_probe rejected_unsigned_fact_explosion examples/rejected_unsigned_fact_explosion.elisa 1
python3 - "$REPORT_DIR/rejected_unsigned_fact_explosion.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["summary"]["semantic_errors"] == 0
assert report["summary"]["proven"] == 2
assert {(f["name"], f["kind"]) for f in report["findings"]} == {
    ("unsigned_fact_explosion", "ensure-unproven"),
    ("unsigned_subtraction_explosion", "ensure-unproven"),
}
PY
run_probe unsigned_local examples/unsigned_local.elisa 0
run_probe rejected_unsigned_local examples/rejected_unsigned_local.elisa 1
run_probe rejected_unsigned_local_states examples/rejected_unsigned_local_states.elisa 1
run_probe unsigned_constant_in_range examples/unsigned_constant_in_range.elisa 0
run_probe rejected_unsigned_constant examples/rejected_unsigned_constant_overflow.elisa 1
run_probe rejected_unsigned_local_constant examples/rejected_unsigned_local_constant_overflow.elisa 1

# Unsigned locals stay symbolic with their compiler width. Every arithmetic goal in
# the rejected fixtures is false under wrapping, stale after a rebinding, or leaks a
# shadowed symbol's facts; none may prove or certify. Only the per-function
# resource-safety obligations, which carry no arithmetic, are admitted.
python3 - "$REPORT_DIR/unsigned_local.json" "$REPORT_DIR/rejected_unsigned_local.json" "$REPORT_DIR/rejected_unsigned_local_states.json" "$REPORT_DIR/unsigned_constant_in_range.json" "$REPORT_DIR/rejected_unsigned_constant.json" "$REPORT_DIR/rejected_unsigned_local_constant.json" <<'PY'
import json
import sys

accepted, *rejected = sys.argv[1:4]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["proven"] == report["summary"]["obligations"] == 16
assert report["findings"] == []
for path in rejected:
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
        raise SystemExit("dogfood failed: unsigned local fixture did not fail cleanly")
    arithmetic_goals = [goal for goal in report["goals"] if goal["rule"] != "resource-safety"]
    if not arithmetic_goals or any(goal["proven"] for goal in arithmetic_goals):
        raise SystemExit("dogfood failed: an unsigned local goal was proven under erased semantics")
    if report["replay"]["certificates"] != len(report["goals"]) - len(arithmetic_goals):
        raise SystemExit("dogfood failed: unsigned local fixture certified an arithmetic goal")

with open(sys.argv[4], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["semantic_errors"] == 0

for path in sys.argv[5:]:
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    if report["status"] != "failed" or report["replay"]["gaps"] != 0:
        raise SystemExit("dogfood failed: unsigned constant overflow fixture did not fail cleanly")
    arithmetic_goals = [goal for goal in report["goals"] if goal["rule"] != "resource-safety"]
    if not arithmetic_goals or any(goal["proven"] for goal in arithmetic_goals):
        raise SystemExit("dogfood failed: an unsigned constant overflow goal was proven")
PY

# This fixture intentionally contains unsupported surface around the standalone replay module.
# A non-zero command verdict is expected, but every certificate it does emit must replay.
run_probe replay_standalone examples/kernel_replay_standalone.elisa 1
run_probe arena_cycle_rejected examples/rejected_kernel_arena_cycle.elisa 1
run_probe structural_shadowed_subterm examples/structural_shadowed_subterm.elisa 0
run_probe rejected_match_shadow_fact examples/rejected_match_shadow_fact.elisa 1
run_probe borrow_four_nested_fields examples/borrow_four_nested_fields.elisa 0
run_probe rejected_borrow_four_nested_alias examples/rejected_borrow_four_nested_alias.elisa 1
run_probe borrow_indexed_places examples/borrow_indexed_places.elisa 0
run_probe rejected_borrow_index_alias examples/rejected_borrow_index_alias.elisa 1
run_probe rejected_borrow_after_move examples/rejected_borrow_after_move.elisa 1
