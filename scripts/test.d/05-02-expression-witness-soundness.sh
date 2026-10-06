# shellcheck shell=bash
# Expression-level witnesses and aggregate equality replay regressions.
# Expression-level type witnesses: struct fields, container counts and elements to the declared
# depth, const-enum values, and verified total-pure call results are witnessed by exact term.
set +e
run_json_report "$ROOT_DIR/examples/expression_witness.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["obligations"] == 44; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"range_binder_reflexive", "element_binder_reflexive", "field_element_binder_reflexive", "element_binder_congruence", "asserted_opaque_binding", "field_reflexive", "nested_field_reflexive", "field_through_reference", "element_reflexive", "count_reflexive", "multi_index_reflexive", "nested_index_reflexive", "field_congruence", "element_equality_symmetry", "local_field_reflexive", "const_enum_reflexive", "pure_call_reflexive", "bound_opaque_call"} <= names; witnesses = [fact for certificate in report["certificates"] for fact in certificate["facts"] if fact["kind"] == "call" and fact["callee"]["name"] in ("__elisa_primitive_scalar_type", "__elisa_primitive_scalar_element")]; assert any(fact["arguments"][0]["kind"] == "field" for fact in witnesses); assert any(fact["callee"]["name"] == "__elisa_primitive_scalar_element" for fact in witnesses)'
expression_witness_status=${PIPESTATUS[1]}
set -e
if [[ "$expression_witness_status" -ne 0 ]]; then
    printf 'proof test matrix failed: expression-level type witnesses\n' >&2
    exit 1
fi

# A const-enum shorthand is admitted only when its declaration is unique and the enum has no
# user-defined Eq implementation. Overloaded equality must remain outside the trusted kernel path.
set +e
run_json_report "$ROOT_DIR/examples/rejected_const_enum_overloaded_equality.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] in ("failed", "unsupported"); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert any(finding["kind"] == "expression-unsupported" for finding in report["findings"]); assert not any(goal["name"] == "reject_overloaded_const_enum_equality" and goal["rule"] == "goal" and goal["proven"] for goal in report["goals"])'
const_enum_overloaded_equality_status=${PIPESTATUS[1]}
set -e
if [[ "$const_enum_overloaded_equality_status" -ne 0 ]]; then
    printf 'proof test matrix failed: const-enum user Eq implementation was treated as built-in\n' >&2
    exit 1
fi

# An owner-neutral shorthand `.Shared` that names a variant of more than one const enum anywhere
# in the source tree, including in a sibling module, gets no scalar witness: its owner is not
# determined by the term alone, so the comparison must stay unproven.
for shorthand_probe in rejected_ambiguous_const_enum_shorthand rejected_module_crossscope_const_enum_shorthand; do
    set +e
    run_json_report "$ROOT_DIR/examples/$shorthand_probe.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] in ("failed", "unsupported"); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert not any(goal["rule"] == "goal" and goal["proven"] for goal in report["goals"]); assert any(goal["rule"] == "goal" and not goal["proven"] for goal in report["goals"])'
    shorthand_probe_status=${PIPESTATUS[1]}
    set -e
    if [[ "$shorthand_probe_status" -ne 0 ]]; then
        printf 'proof test matrix failed: ambiguous const-enum shorthand was witnessed: %s\n' "$shorthand_probe" >&2
        exit 1
    fi
done

# A scalar-field witness for a record element is exact to the selected field; it cannot
# justify congruence for a different field of the same indexed record.
set +e
run_json_report "$ROOT_DIR/examples/record_element_witness.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; goals = report["goals"]; assert any(goal["name"] == "indexed_field_congruence" and goal["proven"] for goal in goals); assert any(goal["name"] == "distinct_field_not_congruent" and not goal["proven"] for goal in goals); assert any(goal["name"] == "nested_indexed_field_congruence" and goal["proven"] for goal in goals); assert any(goal["name"] == "nested_distinct_field_not_congruent" and not goal["proven"] for goal in goals); assert any(goal["name"] == "multi_indexed_field_congruence" and goal["proven"] for goal in goals)'
record_element_witness_status=${PIPESTATUS[1]}
set -e
if [[ "$record_element_witness_status" -ne 0 ]]; then
    printf 'proof test matrix failed: record-element scalar witness escaped its exact field\n' >&2
    exit 1
fi

# The exact-field scalar witness must still defer when the selected primitive operator is
# replaced by user code; a source-level `Eq` implementation is not Leibniz equality.
set +e
run_json_report "$ROOT_DIR/examples/rejected_record_element_overloaded_eq.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] in ("failed", "unsupported"); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert any(goal["name"] == "overloaded_record_element_eq" and goal["rule"] == "goal" and not goal["proven"] for goal in report["goals"]); assert not any(finding["counterexample_found"] for finding in report["findings"])'
record_element_overloaded_eq_status=${PIPESTATUS[1]}
set -e
if [[ "$record_element_overloaded_eq_status" -ne 0 ]]; then
    printf 'proof test matrix failed: record-element primitive equality ignored a source overload\n' >&2
    exit 1
fi

# Aggregate equality must never be proved by the kernel. Newer frontends diagnose tuple equality
# as unsupported; older pinned revisions leave that refusal to proposition formation. Arrays and
# dictionaries are rejected there too, while constructors/updates remain independently replayed.
set +e
run_json_report "$ROOT_DIR/examples/rejected_aggregate_equality.elisa" | python3 -c '
import json, sys
report = json.load(sys.stdin)
assert report["status"] == "failed"
diagnostics = report["semantic_diagnostics"]
assert len(diagnostics) in {0, 2} and all(
    item["message"] == "aggregate values do not support ==; compare their contents explicitly"
    and item["detail"] == "__aggregate"
    for item in diagnostics
), f"unexpected aggregate-equality diagnostics: {diagnostics}"
assert report["summary"]["semantic_errors"] == len(diagnostics)
assert report["replay"]["gaps"] == 0
refused = {"array_equality", "nested_array_equality", "tuple_equality", "dictionary_equality", "construct_equality", "update_equality", "quantified_array_equality", "quantified_tuple_equality", "quantified_dictionary_equality", "quantified_construct_equality"}
claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}
assert not claimed, f"aggregate equality was proved: {claimed}"
assert refused <= {finding["name"] for finding in report["findings"]}
kinds = {node["kind"] for node in report["kernel"]["nodes"]}
assert {"array", "construct", "record-update", "field-init", "quantifier"} <= kinds
'
rejected_aggregate_equality_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_aggregate_equality_status" -ne 0 ]]; then
    printf 'proof test matrix failed: aggregate equality was proved or produced unexpected frontend diagnostics\n' >&2
    exit 1
fi
