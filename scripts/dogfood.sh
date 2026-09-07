#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPILER="${ELISA_COMPILER_BIN:-}"
if [[ -z "$COMPILER" ]]; then
    # `elisac` was a symlink to the Go compiler and is gone; the stage names are
    # explicit now. Prefer the self-hosted compiler. Its objects need the runtime
    # object discovered below; stage0 remains a supported fallback.
    for candidate in elisac-stage1 elisac-stage0 elisac; do
        COMPILER="$(command -v "$candidate" 2>/dev/null || true)"
        [[ -n "$COMPILER" ]] && break
    done
fi
if [[ -z "$COMPILER" ]]; then
    printf 'dogfood failed: set ELISA_COMPILER_BIN to an Elisa compiler\n' >&2
    exit 1
fi

# A stage1 wrapper emits objects that use the self-hosted runtime. Keep this in
# sync with build.sh so the executable dogfood harness exercises the same product
# configuration as the proof binary itself.
RUNTIME_OBJ="${ELISA_RUNTIME_OBJ:-}"
COMPILER_IS_STAGE1=0
if [[ -z "$RUNTIME_OBJ" ]]; then
    driver="$(grep -o '/[^\"]*/scripts/elisac_stage1\.sh' "$COMPILER" 2>/dev/null | head -1 || true)"
    if [[ -n "$driver" ]]; then
        COMPILER_IS_STAGE1=1
        candidate="${driver%/scripts/elisac_stage1.sh}/build/runtime/elisacore_runtime.o"
        [[ -f "$candidate" ]] && RUNTIME_OBJ="$candidate"
    fi
fi
if [[ "$(basename "$COMPILER")" == "elisac-stage1" ]]; then
    COMPILER_IS_STAGE1=1
fi
if [[ "$COMPILER_IS_STAGE1" -eq 1 && -z "$RUNTIME_OBJ" && -f "${HOME}/.elisac/elisacore_runtime.o" ]]; then
    RUNTIME_OBJ="${HOME}/.elisac/elisacore_runtime.o"
fi

"$ROOT_DIR/scripts/build.sh"
# build.sh has just refreshed the snapshot; the executable harnesses below that
# include compiler sources must compile from the same pinned export.
# shellcheck source=scripts/compiler_snapshot.sh
source "$ROOT_DIR/scripts/compiler_snapshot.sh"

REPORT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-dogfood.XXXXXX")"
trap 'rm -rf "$REPORT_DIR"' EXIT

run_probe() {
    local label="$1"
    local source="$2"
    local expected_status="$3"
    local output="$REPORT_DIR/$label.json"
    local repeat_output="$REPORT_DIR/$label.repeat.json"
    set +e
    "$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/$source" >"$output"
    local actual_status=$?
    set -e
    if [[ "$actual_status" -ne "$expected_status" ]]; then
        printf 'dogfood failed: %s exited %s (expected %s)\n' "$label" "$actual_status" "$expected_status" >&2
        return 1
    fi
    set +e
    "$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/$source" >"$repeat_output"
    local repeat_status=$?
    set -e
    if [[ "$repeat_status" -ne "$expected_status" ]]; then
        printf 'dogfood failed: %s changed exit status on repeat (%s vs %s)\n' "$label" "$repeat_status" "$expected_status" >&2
        return 1
    fi
    if ! cmp -s "$output" "$repeat_output"; then
        printf 'dogfood failed: %s produced a non-deterministic proof report\n' "$label" >&2
        return 1
    fi
    python3 - "$label" "$output" <<'PY'
import json
import sys

label, path = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    report = json.load(handle)

replay = report["replay"]
if replay["gaps"] != 0 or replay["certificates"] != replay["replayed"]:
    raise SystemExit(f"dogfood failed: {label} has certificate replay gaps")
if report["kernel"]["independent_replay"] is not True:
    raise SystemExit(f"dogfood failed: {label} did not use independent kernel replay")
print(f"dogfood {label}: status={report['status']} obligations={report['summary']['obligations']} proven={report['summary']['proven']} replay_gaps=0")
PY
}

# The bounds slices and the insertion helper (whose `index` is an unsigned local bound
# to its own typed symbol) prove and replay independently.
run_probe kernel_core src/proof/kernel_core.elisa 0
run_probe kernel_core_fixture examples/dogfood_kernel_core.elisa 0
python3 - "$REPORT_DIR/kernel_core.json" "$REPORT_DIR/kernel_core_fixture.json" <<'PY'
import json
import sys

for path, proven in zip(sys.argv[1:], (7, 20)):
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    assert report["status"] == "proved"
    assert report["summary"]["proven"] == proven
    assert report["summary"]["obligations"] == proven
    assert report["findings"] == []
PY
run_probe quantifier_hypothesis examples/quantifier_hypothesis.elisa 0
run_probe rejected_float_reflexivity examples/rejected_float_reflexivity.elisa 1
run_probe rejected_float_alias examples/rejected_float_alias.elisa 1
run_probe rejected_float_field examples/rejected_float_field.elisa 1
run_probe rejected_float_enum examples/rejected_float_enum.elisa 1
run_probe rejected_float_expression examples/rejected_float_expression.elisa 1
run_probe integer_alias examples/integer_alias.elisa 0
run_probe unsigned_alias examples/unsigned_alias.elisa 0
run_probe rejected_unsigned_alias examples/rejected_unsigned_alias.elisa 1
run_probe unsigned_refinement examples/unsigned_refinement.elisa 0
run_probe rejected_unsigned_refinement examples/rejected_unsigned_refinement.elisa 1
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

# Unsigned locals stay symbolic with their compiler width. Every arithmetic goal in
# the rejected fixtures is false under wrapping, stale after a rebinding, or leaks a
# shadowed symbol's facts; none may prove or certify. Only the per-function
# resource-safety obligations, which carry no arithmetic, are admitted.
python3 - "$REPORT_DIR/unsigned_local.json" "$REPORT_DIR/rejected_unsigned_local.json" "$REPORT_DIR/rejected_unsigned_local_states.json" <<'PY'
import json
import sys

accepted, *rejected = sys.argv[1:]
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
PY

# This fixture intentionally contains unsupported surface around the standalone replay module.
# A non-zero command verdict is expected, but every certificate it does emit must replay.
run_probe replay_standalone examples/kernel_replay_standalone.elisa 1
run_probe arena_cycle_rejected examples/rejected_kernel_arena_cycle.elisa 1
run_probe borrow_four_nested_fields examples/borrow_four_nested_fields.elisa 0
run_probe rejected_borrow_four_nested_alias examples/rejected_borrow_four_nested_alias.elisa 1
run_probe borrow_indexed_places examples/borrow_indexed_places.elisa 0
run_probe rejected_borrow_index_alias examples/rejected_borrow_index_alias.elisa 1
run_probe rejected_borrow_after_move examples/rejected_borrow_after_move.elisa 1
run_probe rejected_negative_affine_difference examples/rejected_negative_affine_difference.elisa 1
run_probe rejected_negative_affine_goal examples/rejected_negative_affine_goal.elisa 1
run_probe rejected_borrow_call_duplicate_alias examples/rejected_borrow_call_duplicate_alias.elisa 1
run_probe rejected_unsigned_overflow_goal examples/rejected_unsigned_overflow_goal.elisa 1
run_probe borrow_multi_indexed_places examples/borrow_multi_indexed_places.elisa 0
run_probe rejected_borrow_multi_index_alias examples/rejected_borrow_multi_index_alias.elisa 1
run_probe borrow_dynamic_whole_root examples/borrow_dynamic_whole_root.elisa 0
run_probe rejected_borrow_dynamic_alias examples/rejected_borrow_dynamic_alias.elisa 1
run_probe borrow_dynamic_multi_whole_root examples/borrow_dynamic_multi_whole_root.elisa 0
run_probe rejected_borrow_dynamic_multi_alias examples/rejected_borrow_dynamic_multi_alias.elisa 1
run_probe borrow_symbolic_disjoint examples/borrow_symbolic_disjoint.elisa 0
run_probe rejected_borrow_symbolic_alias examples/rejected_borrow_symbolic_alias.elisa 1
run_probe for_invariant examples/for_invariant.elisa 0
run_probe for_loop_control_invariant examples/for_loop_control_invariant.elisa 0
run_probe region_allocation examples/region_allocation.elisa 0
run_probe region_scalar_copy examples/region_scalar_copy.elisa 0
run_probe region_statement examples/region_statement.elisa 0
run_probe region_auto_close examples/region_auto_close.elisa 0
run_probe region_generic_allocation examples/region_generic_allocation.elisa 0
run_probe rejected_region_generic_unmapped examples/rejected_region_generic_unmapped.elisa 1
run_probe rejected_region_use_after_destroy examples/rejected_region_use_after_destroy.elisa 1
run_probe rejected_region_destroy_nested_without_binding examples/rejected_region_destroy_nested_without_binding.elisa 1
run_probe rejected_region_duplicate_mutable_alias examples/rejected_region_duplicate_mutable_alias.elisa 1
run_probe rejected_region_assign_duplicate_owner examples/rejected_region_assign_duplicate_owner.elisa 1
run_probe rejected_region_bind_mutable_external examples/rejected_region_bind_mutable_external.elisa 1
run_probe rejected_region_call_result_duplicate_owner examples/rejected_region_call_result_duplicate_owner.elisa 1
run_probe rejected_for_invariant examples/rejected_for_invariant.elisa 1
run_probe rejected_for_invariant_scope examples/rejected_for_invariant_scope.elisa 1
run_probe congruence examples/congruence.elisa 0
run_probe rejected_congruence examples/rejected_congruence.elisa 1
run_probe rejected_reflexivity examples/rejected_reflexivity.elisa 1
run_probe expression_witness examples/expression_witness.elisa 0
run_probe call_stable_facts examples/call_stable_facts.elisa 0
run_probe rejected_call_stable_facts examples/rejected_call_stable_facts.elisa 1
run_probe shared_borrow_calls examples/shared_borrow_calls.elisa 0
run_probe rejected_shared_borrow_calls examples/rejected_shared_borrow_calls.elisa 1
run_probe writable_lend_calls examples/writable_lend_calls.elisa 0
run_probe rejected_writable_lend_calls examples/rejected_writable_lend_calls.elisa 1
run_probe region_lend_calls examples/region_lend_calls.elisa 0
run_probe rejected_region_lend_calls examples/rejected_region_lend_calls.elisa 1
run_probe region_call_summary examples/region_call_summary.elisa 0
run_probe condition_call_positions examples/condition_call_positions.elisa 0
run_probe rejected_condition_call_positions examples/rejected_condition_call_positions.elisa 1
run_probe product_sign examples/product_sign.elisa 0
run_probe rejected_product_sign examples/rejected_product_sign.elisa 1
run_probe frame_lifetime examples/frame_lifetime.elisa 0
run_probe rejected_frame_lifetime examples/rejected_frame_lifetime.elisa 1
run_probe unnamed_lifetime_lend examples/unnamed_lifetime_lend.elisa 1
run_probe rejected_unnamed_lifetime_lend examples/rejected_unnamed_lifetime_lend.elisa 1
run_probe captured_block examples/captured_block.elisa 0
run_probe rejected_captured_block examples/rejected_captured_block.elisa 1
run_probe uncaptured_binding examples/uncaptured_binding.elisa 0
run_probe rejected_uncaptured_binding examples/rejected_uncaptured_binding.elisa 1
run_probe rejected_uncaptured_block_write examples/rejected_uncaptured_block_write.elisa 1
run_probe loop_element_extent examples/loop_element_extent.elisa 1
run_probe rejected_loop_element_extent examples/rejected_loop_element_extent.elisa 1
run_probe comparison_chain_equality examples/comparison_chain_equality.elisa 0
run_probe rejected_comparison_chain_equality examples/rejected_comparison_chain_equality.elisa 1
run_probe region_extent_contract examples/region_extent_contract.elisa 0
run_probe rejected_region_extent_contract examples/rejected_region_extent_contract.elisa 1
run_probe region_statement_call examples/region_statement_call.elisa 0
run_probe rejected_region_statement_call examples/rejected_region_statement_call.elisa 1
run_probe region_lifetime_free_callee examples/region_lifetime_free_callee.elisa 0
run_probe rejected_region_lifetime_free_callee examples/rejected_region_lifetime_free_callee.elisa 1
run_probe short_circuit_guard examples/short_circuit_guard.elisa 0
run_probe rejected_short_circuit_guard examples/rejected_short_circuit_guard.elisa 1
run_probe bound_propagation examples/bound_propagation.elisa 0
run_probe rejected_bound_propagation examples/rejected_bound_propagation.elisa 1
run_probe call_boundary_binding examples/call_boundary_binding.elisa 0
run_probe rejected_call_boundary_binding examples/rejected_call_boundary_binding.elisa 1
run_probe short_circuit_call examples/short_circuit_call.elisa 0
run_probe rejected_short_circuit_call examples/rejected_short_circuit_call.elisa 1
run_probe branch_conjunct_placeholder examples/branch_conjunct_placeholder.elisa 1
run_probe rejected_branch_conjunct_placeholder examples/rejected_branch_conjunct_placeholder.elisa 1
run_probe loop_entry_state examples/loop_entry_state.elisa 1
run_probe rejected_loop_entry_state examples/rejected_loop_entry_state.elisa 1
run_probe loop_condition_facts examples/loop_condition_facts.elisa 1
run_probe rejected_loop_condition_facts examples/rejected_loop_condition_facts.elisa 1
run_probe rejected_shared_extent_global examples/rejected_shared_extent_global.elisa 1
run_probe comparison_chain examples/comparison_chain.elisa 0
run_probe rejected_comparison_chain examples/rejected_comparison_chain.elisa 1
run_probe widened_state_summary examples/widened_state_summary.elisa 1
run_probe rejected_widened_state_summary examples/rejected_widened_state_summary.elisa 1
run_probe rejected_aggregate_equality examples/rejected_aggregate_equality.elisa 1
run_probe rejected_budget examples/rejected_budget.elisa 1
run_probe effect_containment examples/effect_containment.elisa 0
run_probe rejected_effect_containment examples/rejected_effect_containment.elisa 1

# A declared effect row is evidence only when every direct call resolves to a declared callee
# whose row it contains. An exceeded row is a refutation; an unresolved callee is unsupported.
python3 - "$REPORT_DIR/effect_containment.json" "$REPORT_DIR/rejected_effect_containment.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["replay"]["gaps"] == 0
assert report["summary"]["semantic_errors"] == 0
certified = {goal["name"] for goal in report["goals"] if goal["rule"] == "effect-containment"}
if not {"wider_row", "union_row", "exact_row", "no_calls", "calls_rowless"} <= certified:
    raise SystemExit("dogfood failed: a containable effect row was not certified")
rows = {d["name"]: d["effects"] for d in report["declaration_details"] if d["kind"] == "function"}
if rows.get("wider_row") != ["Memory.Allocate", "Abort.Panic"] or rows.get("pure_callee") is not None:
    raise SystemExit("dogfood failed: declared effect rows were not reported")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: adversarial effect fixture did not fail cleanly")
certified = {goal["name"] for goal in report["goals"] if goal["rule"] == "effect-containment"}
if certified & {"narrower_than_callee", "one_uncovered_callee", "opaque_callee"}:
    raise SystemExit("dogfood failed: an uncontained effect row was certified")
kinds = {finding["name"]: (finding["kind"], finding["status"]) for finding in report["findings"]}
expected = {
    "narrower_than_callee": ("effect-row-exceeded", "disproved"),
    "one_uncovered_callee": ("effect-row-exceeded", "disproved"),
    "opaque_callee": ("effect-call-opaque", "unsupported"),
}
for name, want in expected.items():
    if kinds.get(name) != want:
        raise SystemExit("dogfood failed: %s reported %s, wanted %s" % (name, kinds.get(name), want))
PY


# A budget that ran out, a goal no rule decides, and a refuted goal are three different answers.
# The report must keep them apart so an agent repairs the right thing.
python3 - "$REPORT_DIR/rejected_budget.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
if report["replay"]["gaps"] != 0 or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: budget fixture did not fail cleanly")
status = {finding["name"]: finding["status"] for finding in report["findings"]}
expected = {
    "too_wide_quantifier": "timeout",
    "too_large_model": "timeout",
    "unsupported_reasoning": "unknown",
    "false_comparison": "disproved",
    "too_many_congruence_terms": "timeout",
    "too_many_congruence_rounds": "timeout",
    "too_many_disjunctions": "timeout",
    "too_deep_conditional": "timeout",
}
if status != expected:
    raise SystemExit("dogfood failed: verdict states collapsed, got %s" % sorted(status.items()))
PY


# Reflexivity, symmetry, and coherence with arithmetic hold for the language's own operators, not
# for a user `__eq__`/`__cmp__`. No goal here may prove or emit a certificate.
python3 - "$REPORT_DIR/rejected_reflexivity.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: reflexivity fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: reflexivity fixture left a replay gap")
refused = {
    "reflexive_equality",
    "reflexive_order",
    "reflexive_reverse_order",
    "symmetric_equality",
    "local_reflexive_equality",
    "field_reflexive_equality",
    "field_reflexive_order",
    "element_reflexive_equality",
    "opaque_call_reflexive_equality",
    "struct_element_binder_reflexive_equality",
}
claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}
if refused & claimed:
    raise SystemExit("dogfood failed: user-defined equality was assumed reflexive for %s" % sorted(refused & claimed))
if refused - {finding["name"] for finding in report["findings"]}:
    raise SystemExit("dogfood failed: a reflexivity goal produced no diagnostic")
PY


# Ground congruence must carry an equality through every primitive scalar former and through
# no other one. The accepted fixture may not leave a replay gap, and no adversarial goal may prove
# or emit a certificate; only the arithmetic-free resource obligations are admitted there.
python3 - "$REPORT_DIR/congruence.json" "$REPORT_DIR/rejected_congruence.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["proven"] == report["summary"]["obligations"]
assert report["replay"]["gaps"] == 0
assert report["findings"] == []
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: adversarial congruence fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: adversarial congruence fixture left a replay gap")
refused = {
    "disequality_premise",
    "order_premise",
    "disjunctive_premise",
    "unrelated_operand",
    "distinct_former",
    "struct_equality_premise",
    "indexed_element",
    "constructed_aggregate",
    "call_congruence",
    "cross_width",
    "wrapping_operand",
}
claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}
if refused & claimed:
    raise SystemExit("dogfood failed: congruence admitted %s" % sorted(refused & claimed))
if refused - {finding["name"] for finding in report["findings"]}:
    raise SystemExit("dogfood failed: an adversarial congruence goal produced no diagnostic")
PY

# A comparison concluded from two terms denoting the same value needs both operands witnessed as
# primitive scalars. The producer witnesses struct fields, container counts and elements, and
# verified total-pure call results by exact term; an aggregate comparison has no witness at all.
python3 - "$REPORT_DIR/expression_witness.json" "$REPORT_DIR/rejected_aggregate_equality.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["proven"] == report["summary"]["obligations"]
assert report["replay"]["gaps"] == 0
assert report["findings"] == []
witnesses = [fact for certificate in report["certificates"] for fact in certificate["facts"] if fact["kind"] == "call" and fact["callee"]["name"] in ("__elisa_primitive_scalar_type", "__elisa_primitive_scalar_element")]
if not any(fact["arguments"][0]["kind"] == "field" for fact in witnesses):
    raise SystemExit("dogfood failed: no field witness reached a certificate")
if not any(fact["arguments"][0]["kind"] == "call" for fact in witnesses):
    raise SystemExit("dogfood failed: no verified pure call witness reached a certificate")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: aggregate equality fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: aggregate equality fixture left a replay gap")
claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}
if claimed:
    raise SystemExit("dogfood failed: aggregate equality admitted for %s" % sorted(claimed))
print("dogfood expression_witness: term-keyed type witnesses admit exactly the primitive scalar places")
PY

# A callee reaches the caller only through references and globals, and a conjunctive guard entails
# each of its parts. Together they carry a bounded-recursion precondition past an opaque call; the
# conjuncts are derived facts, so every certificate that uses one must still replay without gaps.
python3 - "$REPORT_DIR/call_stable_facts.json" "$REPORT_DIR/rejected_call_stable_facts.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["summary"]["proven"] != report["summary"]["obligations"]:
    raise SystemExit("dogfood failed: call-stable fixture did not prove")
if report["replay"]["gaps"] != 0 or report["findings"] != []:
    raise SystemExit("dogfood failed: call-stable fixture left a gap or a finding")
origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}
if "branch-conjunct" not in origins:
    raise SystemExit("dogfood failed: no branch conjunct reached a certificate")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: call-stable boundary fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: call-stable boundary fixture left a replay gap")
refused = {"aliased_scalar", "assigned_in_branch", "disjunctive_branch", "negated_conjunctive_guard", "rebound_after_guard"}
missing = refused - {finding["name"] for finding in report["findings"]}
if missing:
    raise SystemExit("dogfood failed: no diagnostic for %s" % sorted(missing))
print("dogfood call_stable_facts: facts survive exactly the calls and joins that cannot falsify them")
PY

# Lending only shared references leaves the caller's resource state untouched, so such a call needs
# no callee body summary. Every one of them must still appear in the trace as an explicit
# shared-read transition, and a writable or escaping capability must still be refused.
python3 - "$REPORT_DIR/shared_borrow_calls.json" "$REPORT_DIR/rejected_shared_borrow_calls.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["summary"]["proven"] != report["summary"]["obligations"]:
    raise SystemExit("dogfood failed: shared-reference call fixture did not prove")
if report["replay"]["gaps"] != 0 or report["findings"] != []:
    raise SystemExit("dogfood failed: shared-reference call fixture left a gap or a finding")
shared = [node for node in report["kernel"]["nodes"] if node["kind"] == "resource-call-lend"]
if not shared:
    raise SystemExit("dogfood failed: no shared-read call reached the arena")
if any(node["left"] != 0 or node["children_count"] != node["auxiliary"] * 2 for node in shared):
    raise SystemExit("dogfood failed: a shared-read call carried a callee summary root")
nodes = report["kernel"]["nodes"]
children = report["kernel"]["children"]
formals = [nodes[child] for node in shared for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]
if not formals or any(formal["kind"] != "resource-call-formal" for formal in formals):
    raise SystemExit("dogfood failed: a shared-read call recorded no callee parameter modes")
if any(formal["operator"] not in ("value", "external-shared") for formal in formals):
    raise SystemExit("dogfood failed: an exclusive callee formal was recorded under a shared read")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0:
    raise SystemExit("dogfood failed: shared-reference boundary fixture did not fail cleanly")
if report["replay"]["gaps"] != 0:
    raise SystemExit("dogfood failed: shared-reference boundary fixture left a replay gap")
findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}
required = {("borrow-call-opaque", "recursive_reference_return"), ("borrow-call-opaque", "lends_shared_while_mutably_borrowed"), ("resource-use-after-move", "lends_moved_value")}
missing = required - findings
if missing:
    raise SystemExit("dogfood failed: no diagnostic for %s" % sorted(missing))
if any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"]):
    raise SystemExit("dogfood failed: an escaping, moved or exclusively borrowed capability was recorded as a lend")
opaque = {finding["name"] for finding in report["findings"] if finding["kind"] == "borrow-call-opaque"}
if "lends_shared_while_mutably_borrowed" not in opaque:
    raise SystemExit("dogfood failed: a shared lend across a live exclusive borrow was not refused")
print("dogfood shared_borrow_calls: shared lending needs no callee summary")
PY

# An exclusive lend needs no callee summary either. The callee can do no more than write through
# the reference, so the caller records a write to the whole lent place; every exclusive capability
# must be one the caller holds alone, with no overlapping live borrow and no overlapping co-lend.
python3 - "$REPORT_DIR/writable_lend_calls.json" "$REPORT_DIR/rejected_writable_lend_calls.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: confined writable lending did not prove cleanly")
nodes = report["kernel"]["nodes"]
children = report["kernel"]["children"]
lends = [node for node in nodes if node["kind"] == "resource-call-lend"]
if not lends:
    raise SystemExit("dogfood failed: no confined lend reached the arena")
formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]
if not any(formal["operator"] == "external-mutable" for formal in formals):
    raise SystemExit("dogfood failed: no exclusive lend was recorded")
if any(formal["kind"] != "resource-call-formal" for formal in formals):
    raise SystemExit("dogfood failed: a confined lend recorded no callee parameter modes")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0 or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: exclusive-lend boundary fixture did not fail cleanly")
if any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"]):
    raise SystemExit("dogfood failed: an unconfined exclusive capability was recorded as a lend")
opaque = {finding["name"] for finding in report["findings"] if finding["kind"] == "borrow-call-opaque"}
for name in ("swap_pair", "read_and_write", "touch_borrowed"):
    if name not in opaque:
        raise SystemExit("dogfood failed: %s was not refused" % name)
print("dogfood writable_lend_calls: an exclusive lend is confined to a whole-place write")
PY

# A lifetime parameter does not stop a call from being a lend. The callee may allocate into a
# mapped caller region and can never close one, so the claim is the lifetime pinning itself:
# every formal lifetime resolves to a region active at the call and to the actual's own region.
python3 - "$REPORT_DIR/region_lend_calls.json" "$REPORT_DIR/rejected_region_lend_calls.json" <<'PY'
import json
import sys

accepted, rejected = sys.argv[1:]
with open(accepted, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "proved" or report["findings"] or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: region-polymorphic lending did not prove cleanly")
nodes = report["kernel"]["nodes"]
children = report["kernel"]["children"]
lends = [node for node in nodes if node["kind"] == "resource-call-lend" and node["right"] > 0]
if not lends:
    raise SystemExit("dogfood failed: no lifetime-carrying lend reached the arena")
for node in lends:
    if node["children_count"] != node["auxiliary"] * 2 + node["right"]:
        raise SystemExit("dogfood failed: a lend child list does not match its parameter and lifetime counts")
    entries = [nodes[child] for child in children[node["children_start"] + node["auxiliary"] * 2:node["children_start"] + node["children_count"]]]
    if any(entry["kind"] != "resource-call-region" or entry["operator"] != "param" or not entry["name"] or not entry["secondary_name"] for entry in entries):
        raise SystemExit("dogfood failed: a lifetime map entry is malformed")
    if len({entry["name"] for entry in entries}) != len(entries):
        raise SystemExit("dogfood failed: a formal lifetime was pinned twice")
with open(rejected, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["summary"]["semantic_errors"] != 0 or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: lifetime boundary fixture did not fail cleanly")
if any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"]):
    raise SystemExit("dogfood failed: an unpinned lifetime was recorded as a lend")
print("dogfood region_lend_calls: a lifetime parameter is pinned, never assumed")
PY

# A region-polymorphic callee that does have a summary must compose into its caller. This replayed
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
    if (owner, "region-contract-unsupported") not in owners:
        raise SystemExit("dogfood failed: %s entered a contract as if it were an extent" % owner)
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
for owner in ("increment_under_a_bounded_limit", "increment_through_a_chain", "lower_bound_travels", "unsigned_increment_under_a_strict_peer", "unsigned_increment_under_a_reversed_peer"):
    if (owner, "goal") not in proven:
        raise SystemExit("dogfood failed: %s did not reach the overflow guard with its interval" % owner)
with open(invented, encoding="utf-8") as handle:
    report = json.load(handle)
if report["status"] != "failed" or report["replay"]["gaps"]:
    raise SystemExit("dogfood failed: bound propagation boundary fixture did not fail cleanly")
goals = {(goal["name"], goal["rule"]): goal["proven"] for goal in report["goals"]}
for owner in ("unsigned_step_of_two", "unsigned_increment_under_a_non_strict_peer", "unsigned_peer_of_another_name", "lower_bound_does_not_bound_above", "non_strict_premise_is_not_shiftable", "bound_on_an_unrelated_name"):
    if goals.get((owner, "goal")) is not False:
        raise SystemExit("dogfood failed: %s was given an interval nothing established" % owner)
print("dogfood bound_propagation: a constraint carries an interval it already implies, and no other")
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
expected = {("skipped_call_must_not_establish_and", "ensure-unproven"), ("skipped_call_must_not_establish_or", "ensure-unproven"), ("skipped_call_must_not_establish_a_guard", "ensure-unproven"), ("pre_call_value_must_not_survive", "ensure-unproven"), ("skipped_requires_is_still_checked", "call-requires-unproven")}
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
for entry in (("struct_order_is_not_transitive", "goal"), ("struct_non_strict_order_is_not_transitive", "goal"), ("non_strict_chain_gives_no_strict_goal", "goal"), ("wrong_direction_chain", "goal")):
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
    clang -Wl,-dead_strip -o "$runtime_dir/program" "$runtime_dir/program.o" "$RUNTIME_OBJ"
else
    "$COMPILER" -emit obj -O0 -o "$runtime_dir/runtime-support.o" "$runtime_source" >/dev/null 2>&1
    clang -Wl,-dead_strip -o "$runtime_dir/program" "$runtime_dir/program.o" "$runtime_dir/runtime-support.o"
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

"$COMPILER" -emit obj -O0 -o "$runtime_dir/comparison-runtime.o" "$ROOT_DIR/examples/kernel_comparison_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/comparison-runtime" "$runtime_dir/comparison-runtime.o" "$RUNTIME_OBJ"
else
    clang -Wl,-dead_strip -o "$runtime_dir/comparison-runtime" "$runtime_dir/comparison-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/comparison-runtime"
printf 'dogfood comparison_runtime: six witnessed comparisons checked, and unwitnessed reflexivity refused\n'

# Congruence closure is exercised against the kernel directly: every participating former must
# carry an equality, and every excluded former (call, move, address-of, namespace path, guarded
# access, quantifier) must refuse to, on both the dedicated rule and full goal replay.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/congruence-runtime.o" "$ROOT_DIR/examples/kernel_congruence_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/congruence-runtime" "$runtime_dir/congruence-runtime.o" "$RUNTIME_OBJ"
else
    clang -Wl,-dead_strip -o "$runtime_dir/congruence-runtime" "$runtime_dir/congruence-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/congruence-runtime"
printf 'dogfood congruence_runtime: participating formers carried equalities and excluded formers refused\n'

# Propositional fact projection is exercised against the kernel directly: a conjunction entails
# each conjunct, a negated disjunction entails each negated disjunct, a double negation cancels,
# and the dual forms - a disjunction, a negated conjunction - must stay refused in both signs.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/projection-runtime.o" "$ROOT_DIR/examples/kernel_projection_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/projection-runtime" "$runtime_dir/projection-runtime.o" "$RUNTIME_OBJ"
else
    clang -Wl,-dead_strip -o "$runtime_dir/projection-runtime" "$runtime_dir/projection-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/projection-runtime"
printf 'dogfood projection_runtime: conjunct and negated-disjunct projection admitted, duals refused\n'

# Declared effect containment is checked against the kernel directly: contained rows admitted,
# uncontained rows refused, and every malformed effect graph rejected rather than interpreted.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/effect-runtime.o" "$ROOT_DIR/examples/kernel_effect_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/effect-runtime" "$runtime_dir/effect-runtime.o" "$RUNTIME_OBJ"
else
    clang -Wl,-dead_strip -o "$runtime_dir/effect-runtime" "$runtime_dir/effect-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/effect-runtime"
printf 'dogfood effect_runtime: contained rows admitted and uncontained or malformed rows refused\n'

# Bootstrap coverage: compile the runtime with stage0 as well; an installed stage1
# runtime is not an implicit bootstrap dependency. The reduced resource trace
# guards the stage0 miscompile of allocations made through an unannotated mutable
# reference inside a region-polymorphic function (see AUDIT.md); the full arena
# harness then confirms the whole replay layer under the bootstrap compiler.
bootstrap_compiler="$(command -v elisac-stage0 2>/dev/null || true)"
if [[ -n "$bootstrap_compiler" ]]; then
    "$bootstrap_compiler" -emit obj -O0 -o "$runtime_dir/bootstrap-runtime.o" "$runtime_source" >/dev/null 2>&1
    for bootstrap_example in kernel_comparison_runtime kernel_congruence_runtime kernel_projection_runtime kernel_effect_runtime kernel_resource_bootstrap_runtime kernel_arena_runtime; do
        "$bootstrap_compiler" -emit obj -O0 -o "$runtime_dir/bootstrap-$bootstrap_example.o" "$ROOT_DIR/examples/$bootstrap_example.elisa" >/dev/null 2>&1
        clang -Wl,-dead_strip -o "$runtime_dir/bootstrap-$bootstrap_example" "$runtime_dir/bootstrap-$bootstrap_example.o" "$runtime_dir/bootstrap-runtime.o"
        set +e
        "$runtime_dir/bootstrap-$bootstrap_example"
        bootstrap_status=$?
        set -e
        if [[ "$bootstrap_status" -ne 0 ]]; then
            printf 'dogfood failed: stage0-built %s exited %s\n' "$bootstrap_example" "$bootstrap_status" >&2
            exit 1
        fi
        printf 'dogfood bootstrap_%s: stage0 harness passed\n' "$bootstrap_example"
    done
else
    printf 'dogfood bootstrap: skipped (elisac-stage0 unavailable)\n'
fi

# Exercise the Elisa-native proof-state action layer itself. This is intentionally an
# executable harness rather than a report-only probe: both branches of split/cases must solve,
# rewrite requires an explicit equality, and a rejected action must leave the state unsolved.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/tactic-runtime.o" "$SNAPSHOT_ROOT/examples/tactic_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/tactic-runtime" "$runtime_dir/tactic-runtime.o" "$RUNTIME_OBJ"
else
    clang -Wl,-dead_strip -o "$runtime_dir/tactic-runtime" "$runtime_dir/tactic-runtime.o"
fi
set +e
"$runtime_dir/tactic-runtime"
tactic_status=$?
set -e
if [[ "$tactic_status" -ne 0 ]]; then
    printf 'dogfood failed: executable tactic action suite failed (exit %s)\n' "$tactic_status" >&2
    exit 1
fi
printf 'dogfood tactic_runtime: kernel-backed state actions and branch obligations passed\n'

# Corrupt a checked lemma-summary binding in memory and require independent replay to reject every
# caller certificate that tries to consume the now-mismatched instantiated postcondition.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/lemma-summary-replay.o" "$SNAPSHOT_ROOT/examples/lemma_summary_replay_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/lemma-summary-replay" "$runtime_dir/lemma-summary-replay.o" "$RUNTIME_OBJ"
else
    clang -Wl,-dead_strip -o "$runtime_dir/lemma-summary-replay" "$runtime_dir/lemma-summary-replay.o"
fi
set +e
"$runtime_dir/lemma-summary-replay"
lemma_summary_replay_status=$?
set -e
if [[ "$lemma_summary_replay_status" -ne 0 ]]; then
    printf 'dogfood failed: forged lemma summary survived replay (exit %s)\n' "$lemma_summary_replay_status" >&2
    exit 1
fi
printf 'dogfood summary_replay: mismatched lemma/function instantiations and AST/kernel drift rejected\n'

# Portable proof scripts are parsed and executed by the Elisa implementation itself. The
# script's source fingerprint is optional for reusable theorem states, but when present a stale
# script must fail even if its proposition is independently true.
portable_output="$REPORT_DIR/tactic-script.json"
portable_repeat_output="$REPORT_DIR/tactic-script.repeat.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script.json" "$ROOT_DIR/examples/verified.elisa" >"$portable_output"
portable_status=$?
set -e
if [[ "$portable_status" -ne 0 ]]; then
    printf 'dogfood failed: portable tactic script was not admitted (exit %s)\n' "$portable_status" >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script.json" "$ROOT_DIR/examples/verified.elisa" >"$portable_repeat_output"
portable_repeat_status=$?
set -e
if [[ "$portable_repeat_status" -ne 0 ]] || ! cmp -s "$portable_output" "$portable_repeat_output"; then
    printf 'dogfood failed: portable tactic script was non-deterministic\n' >&2
    exit 1
fi
python3 - "$portable_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
tactic = report["tactic"]
assert report["format"] == "elisa-proof-tactic-result-v1"
assert report["status"] == "proved"
assert report["source"]["status"] == "proved"
assert tactic["valid"] is True
assert tactic["solved"] is True
assert tactic["trace_replayed"] is True
assert tactic["kernel_trace_replayed"] is True
assert tactic["kernel_replayed"] is True
assert tactic["certificate_replayed"] is True
assert tactic["action_count"] == 2
assert len(report["state"]["trace"]) == 2
print("dogfood tactic_script: portable JSON trace and certificate passed")
PY
branch_output="$REPORT_DIR/tactic-script-branch.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_branch.json" "$ROOT_DIR/examples/verified.elisa" >"$branch_output"
branch_status=$?
set -e
if [[ "$branch_status" -ne 0 ]]; then
    printf 'dogfood failed: portable branch tactic script was not admitted (exit %s)\n' "$branch_status" >&2
    exit 1
fi
python3 - "$branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
tactic = report["tactic"]
assert report["status"] == "proved"
assert tactic["branch_present"] is True
assert tactic["branch_certificate_replayed"] is True
assert tactic["trace_replayed"] is True
assert tactic["kernel_trace_replayed"] is True
assert tactic["kernel_replayed"] is True
assert tactic["certificate_replayed"] is True
assert report["state"]["trace"][-1]["action"] == "split"
assert report["branches"]["left"]["solved"] is True
assert report["branches"]["right"]["solved"] is True
assert len(report["branches"]["left"]["trace"]) == 1
assert len(report["branches"]["right"]["trace"]) == 1
print("dogfood tactic_script_branch: both serialized child certificates replayed")
PY
nested_branch_output="$REPORT_DIR/tactic-script-nested-branch.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_branch.json" "$ROOT_DIR/examples/verified.elisa" >"$nested_branch_output"
nested_branch_status=$?
set -e
if [[ "$nested_branch_status" -ne 0 ]]; then
    printf 'dogfood failed: nested portable branch tactic script was not admitted (exit %s)\n' "$nested_branch_status" >&2
    exit 1
fi
python3 - "$nested_branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
tactic = report["tactic"]
assert report["status"] == "proved"
assert tactic["branch_present"] is True
assert tactic["branch_certificate_replayed"] is True
assert tactic["certificate_replayed"] is True
nested = report["branches"]["left"]
assert nested["branches"]["left"]["solved"] is True
assert nested["branches"]["right"]["solved"] is True
assert report["branches"]["right"]["solved"] is True
print("dogfood tactic_script_nested_branch: recursively replayed branch tree passed")
PY
nested_cases_output="$REPORT_DIR/tactic-script-nested-cases.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_cases.json" "$ROOT_DIR/examples/verified.elisa" >"$nested_cases_output"
nested_cases_status=$?
set -e
if [[ "$nested_cases_status" -ne 0 ]]; then
    printf 'dogfood failed: nested portable cases tactic script was not admitted (exit %s)\n' "$nested_cases_status" >&2
    exit 1
fi
python3 - "$nested_cases_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["tactic"]["branch_certificate_replayed"] is True
nested = report["branches"]["left"]
assert nested["trace"][-1]["action"] == "cases"
assert nested["branches"]["left"]["facts"] == [{"kind": "bool", "value": True}]
assert nested["branches"]["right"]["facts"] == [{"kind": "bool", "value": True}]
print("dogfood tactic_script_nested_cases: recursive disjunction context replay passed")
PY
source_nested_branch_output="$REPORT_DIR/tactic-script-target-nested-branch.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target_nested_branch.json" "$ROOT_DIR/examples/verified_branch.elisa" >"$source_nested_branch_output"
source_nested_branch_status=$?
set -e
if [[ "$source_nested_branch_status" -ne 0 ]]; then
    printf 'dogfood failed: source-bound nested branch tactic script was not admitted (exit %s)\n' "$source_nested_branch_status" >&2
    exit 1
fi
python3 - "$source_nested_branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
binding = report["source_goal_binding"]
assert binding["bound"] and binding["goal_id"] == 1 and binding["previously_proven"]
assert binding["fingerprint_match"] is True
assert report["tactic"]["certificate_replayed"] is True
assert report["branches"]["left"]["branches"]["right"]["solved"] is True
print("dogfood tactic_script_target_nested_branch: source-bound tree certificate passed")
PY
incomplete_branch_output="$REPORT_DIR/tactic-script-branch-incomplete.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_branch_incomplete.json" "$ROOT_DIR/examples/verified.elisa" >"$incomplete_branch_output"
incomplete_branch_status=$?
set -e
if [[ "$incomplete_branch_status" -ne 1 ]]; then
    printf 'dogfood failed: incomplete portable branch tactic script was accepted (exit %s)\n' "$incomplete_branch_status" >&2
    exit 1
fi
python3 - "$incomplete_branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["tactic"]["branch_present"] is True
assert report["tactic"]["branch_certificate_replayed"] is False
assert report["tactic"]["certificate_replayed"] is False
assert report["branches"]["left"]["solved"] is True
assert report["branches"]["right"]["solved"] is False
print("dogfood tactic_script_branch_incomplete: an open child blocked admission")
PY
target_output="$REPORT_DIR/tactic-script-target.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target.json" "$ROOT_DIR/examples/verified.elisa" >"$target_output"
target_status=$?
set -e
if [[ "$target_status" -ne 0 ]]; then
    printf 'dogfood failed: source-bound tactic script was not admitted (exit %s)\n' "$target_status" >&2
    exit 1
fi
python3 - "$target_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
binding = report["source_goal_binding"]
assert report["status"] == "proved"
assert binding["bound"] and binding["goal_id"] == 7 and binding["previously_proven"]
assert binding["fingerprint_match"] is True
assert report["tactic"]["status"] == "proved"
assert report["tactic"]["certificate_replayed"] is True
assert len(report["state"]["initial_facts"]) == 2
assert any(
    fact["kind"] == "call" and fact["callee"]["name"] == "__elisa_primitive_scalar_type"
    for fact in report["state"]["initial_facts"]
)
assert report["state"]["initial_goal"] == report["state"]["goal"]
print("dogfood tactic_script_target: imported goal and facts were bound before replay")
PY
repair_target_output="$REPORT_DIR/tactic-script-repair-target.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" >"$repair_target_output"
repair_target_status=$?
set -e
if [[ "$repair_target_status" -ne 0 ]]; then
    printf 'dogfood failed: source-bound tactic did not repair an open goal (exit %s)\n' "$repair_target_status" >&2
    exit 1
fi
python3 - "$repair_target_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["admission_scope"] == "target"
assert report["source"]["status"] == "failed"
assert report["source"]["complete"] is False
assert report["source"]["admissible"] is True
binding = report["source_goal_binding"]
assert binding["bound"] and binding["goal_id"] == 1 and not binding["previously_proven"]
assert binding["goal_fingerprint"]["value"] == 3193966897
assert binding["fingerprint_match"] is True
assert report["tactic"]["certificate_replayed"] is True
assert [step["action"] for step in report["state"]["trace"]] == ["rewrite", "decide"]
print("dogfood tactic_script_repair_target: an open imported goal was independently repaired")
PY
forged_target_output="$REPORT_DIR/tactic-script-target-forged.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target_forged.json" "$ROOT_DIR/examples/verified.elisa" >"$forged_target_output"
forged_target_status=$?
set -e
if [[ "$forged_target_status" -ne 1 ]]; then
    printf 'dogfood failed: source-bound tactic script accepted a forged initial state (exit %s)\n' "$forged_target_status" >&2
    exit 1
fi
python3 - "$forged_target_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
binding = report["source_goal_binding"]
assert binding["bound"] and binding["goal_id"] == 7 and binding["previously_proven"]
assert report["tactic"]["valid"] is False
assert report["state"]["initial_goal"] == {"kind": "invalid"}
assert "source-bound" in report["tactic"]["reason"]
print("dogfood tactic_script_target_forged: imported state could not be replaced")
PY
forged_quantifier_output="$REPORT_DIR/tactic-script-source-bound-forged-quantifier.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_source_bound_forged_quantifier.json" "$ROOT_DIR/examples/rejected_source_bound_exists.elisa" >"$forged_quantifier_output"
forged_quantifier_status=$?
set -e
if [[ "$forged_quantifier_status" -ne 1 ]]; then
    printf 'dogfood failed: source-bound tactic weakened a universal quantifier (exit %s)\n' "$forged_quantifier_status" >&2
    exit 1
fi
python3 - "$forged_quantifier_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["status"] == "failed"
assert report["source"]["admissible"] is True
assert report["tactic"]["valid"] is False
assert report["tactic"]["solved"] is False
assert report["state"]["action_count"] == 1
assert report["state"]["trace"][0]["accepted"] is False
assert report["state"]["initial_goal"]["kind"] == "block"
print("dogfood tactic_script_source_bound_forged_quantifier: compiler quantifier kind remained authoritative")
PY
forged_instantiation_output="$REPORT_DIR/forged-instantiation.json"
if "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_source_bound_forged_instantiation.json" "$ROOT_DIR/examples/source_bound_exists.elisa" >"$forged_instantiation_output"; then
    printf 'dogfood failed: existential source hypothesis admitted universal instantiation\n' >&2
    exit 1
fi
python3 - "$forged_instantiation_output" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["admissible"] is True
assert report["tactic"]["certificate_replayed"] is False
assert report["state"]["initial_facts"][0]["kind"] == "block"
assert report["state"]["trace"][0]["action"] == "instantiate"
assert report["state"]["trace"][0]["accepted"] is False
print("dogfood forged_instantiation: existential hypothesis cannot be relabeled universal")
PY
exact_integer_output="$REPORT_DIR/tactic-integer-exact.json"
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_integer_rounding.json" "$ROOT_DIR/examples/tactic_integer_exact_boundary.elisa" >"$exact_integer_output"
python3 - "$exact_integer_output" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["tactic"]["certificate_replayed"] is True
assert report["state"]["initial_goal"]["left"]["value"] == 9007199254740991
PY
rounding_output="$REPORT_DIR/tactic-integer-rounding.json"
if "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_integer_rounding.json" "$ROOT_DIR/examples/rejected_tactic_integer_rounding.elisa" >"$rounding_output"; then
    printf 'dogfood failed: rounded integers admitted a false source equality\n' >&2
    exit 1
fi
python3 - "$rounding_output" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["admissible"] is True
assert report["source_goal_binding"]["previously_proven"] is False
assert report["tactic"]["valid"] is False
assert report["tactic"]["certificate_replayed"] is False
print("dogfood integer_rounding: lossy JSON numbers cannot prove a different source goal")
PY
stale_output="$REPORT_DIR/tactic-script-stale.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_stale.json" "$ROOT_DIR/examples/verified.elisa" >"$stale_output"
stale_status=$?
set -e
if [[ "$stale_status" -ne 1 ]]; then
    printf 'dogfood failed: stale portable tactic script was accepted (exit %s)\n' "$stale_status" >&2
    exit 1
fi
python3 - "$stale_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["fingerprint_match"] is False
assert report["tactic"]["certificate_replayed"] is True
assert "source_fingerprint" in report["tactic"]["reason"]
print("dogfood tactic_script_stale: source binding rejected stale certificate")
PY

if [[ "${ELISA_DOGFOOD_FULL:-0}" == "1" ]]; then
    # The complete implementation is currently an audit target, not a self-trust exception:
    # unsupported compiler/proof-language boundaries are expected to keep this report failed.
    run_probe full_implementation src/main.elisa 1
fi

printf 'dogfood audit passed: formalized layers are replay-complete\n'
