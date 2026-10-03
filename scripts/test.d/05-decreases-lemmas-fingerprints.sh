# shellcheck shell=bash
# Part 5 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
"$ROOT_DIR/build/elisa-proof" --goal -1 "$ROOT_DIR/examples/verified.elisa" >/dev/null
focused_negative_goal_status=$?
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/lemma.elisa" | python3 -c 'import json, sys; catalog = json.load(sys.stdin); assert catalog["format"] == "elisa-proof-theorems-v1"; assert catalog["source"]["complete"] is True; assert [item["name"] for item in catalog["theorems"]] == ["nonnegative", "named_nonnegative"]; assert all(item["verified"] and item["signature_valid"] and item["proof_goals_valid"] and item["proof_replay_complete"] for item in catalog["theorems"]); assert all(theorem["proof_goals"] and all(goal["proven"] and goal["replayed"] and isinstance(goal["certificate_id"], int) for goal in theorem["proof_goals"]) for theorem in catalog["theorems"]); assert catalog["theorems"][0]["parameters"] == ["x"]; assert catalog["theorems"][0]["parameter_types"] == [{"kind": "ident", "name": "i64", "line": 1}]; assert [item["name"] for item in catalog["theorems"][1]["parameter_types"]] == ["i64", "i64"]; assert len(catalog["theorems"][1]["requires"]) == 2; assert len(catalog["theorems"][1]["ensures"]) == 1'
theorem_catalog_statuses=("${PIPESTATUS[@]}")
theorem_catalog_status=${theorem_catalog_statuses[0]}
theorem_catalog_json_status=${theorem_catalog_statuses[1]}
run_json_report "$ROOT_DIR/examples/lemma.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); traces = [trace for trace in report["kernel"]["fact_traces"] if trace["kind"] == "lemma-summary"]; assert report["status"] == "proved" and report["replay"]["gaps"] == 0; assert [trace["dependency"] for trace in traces] == ["nonnegative", "named_nonnegative"]; assert [len(trace["summary_bindings"]) for trace in traces] == [1, 2]; assert [len(trace["summary_require_goal_ids"]) for trace in traces] == [1, 2]; assert all(trace["summary_ensure_index"] == 0 for trace in traces); goals = report["goals"]; assert all(all(goals[goal_id]["proven"] and goals[goal_id]["replay_status"] == "replayed" for goal_id in trace["summary_require_goal_ids"]) for trace in traces)'
lemma_summary_provenance_statuses=("${PIPESTATUS[@]}")
lemma_summary_provenance_status=${lemma_summary_provenance_statuses[0]}
lemma_summary_provenance_json_status=${lemma_summary_provenance_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/rejected_lemma.elisa" | python3 -c 'import json, sys; catalog = json.load(sys.stdin); assert catalog["source"]["complete"] is False; assert len(catalog["theorems"]) == 1; theorem = catalog["theorems"][0]; assert theorem["name"] == "unsound"; assert theorem["verified"] is False; assert theorem["verification_reason"] == "body-unverified"; assert theorem["signature_valid"] is True; assert theorem["proof_goals_valid"] is True; assert theorem["proof_replay_complete"] is False; assert any(not goal["proven"] and goal["certificate_id"] is None and not goal["replayed"] for goal in theorem["proof_goals"])'
rejected_theorem_catalog_statuses=("${PIPESTATUS[@]}")
rejected_theorem_catalog_status=${rejected_theorem_catalog_statuses[0]}
rejected_theorem_catalog_json_status=${rejected_theorem_catalog_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --theorems "$ROOT_DIR/examples/lemma_default_catalog.elisa" | python3 -c 'import json, sys; theorem = json.load(sys.stdin)["theorems"][0]; assert theorem["verified"] is True; assert theorem["parameters"] == ["x", "amount"]; assert theorem["parameter_defaults"] == [None, {"kind": "int", "value": 7}]'
default_theorem_catalog_statuses=("${PIPESTATUS[@]}")
default_theorem_catalog_status=${default_theorem_catalog_statuses[0]}
default_theorem_catalog_json_status=${default_theorem_catalog_statuses[1]}
python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/theorem_fingerprint_a.elisa" "$ROOT_DIR/examples/theorem_fingerprint_b.elisa" "$ROOT_DIR/examples/theorem_fingerprint_changed.elisa" <<'PY'
import json, subprocess, sys
def fingerprint(path):
    catalog = json.loads(subprocess.check_output([sys.argv[1], "--theorems", path]))
    theorem = next(item for item in catalog["theorems"] if item["name"] == "stable_identity")
    assert theorem["theorem_fingerprint"]["algorithm"] == "fnv1a32-kernel-theorem-v2"
    return theorem["theorem_fingerprint"]["value"]
original = fingerprint(sys.argv[2])
shifted = fingerprint(sys.argv[3])
changed = fingerprint(sys.argv[4])
assert original == shifted
assert original != changed
PY
stable_theorem_fingerprint_status=$?
"$ROOT_DIR/build/elisa-proof" --suggest 4 "$ROOT_DIR/examples/theorem_suggestions.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["format"] == "elisa-proof-suggestions-v1"; assert result["status"] == "ok"; assert result["source"]["admissible"] is True; assert result["goal_id"] == 4; assert result["goal_fingerprint"]["algorithm"] == "fnv1a32-kernel-goal-v2"; assert isinstance(result["goal_fingerprint"]["value"], int); assert len(result["candidates"]) == 1; candidate = result["candidates"][0]; assert candidate["theorem"] == "double_three"; assert candidate["ensure_index"] == 0; assert candidate["bindings"][0]["parameter"] == "value"; assert candidate["bindings"][0]["value"]["operator"] == "+"; assert candidate["premises"][0]["satisfied"] is True; assert candidate["premises_satisfied"] is True; assert candidate["applicable"] is True'
theorem_suggestion_statuses=("${PIPESTATUS[@]}")
theorem_suggestion_status=${theorem_suggestion_statuses[0]}
theorem_suggestion_json_status=${theorem_suggestion_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --suggest 1 "$ROOT_DIR/examples/rejected_lemma.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["source"]["admissible"] is False; assert result["candidates"] == []'
unverified_theorem_suggestion_statuses=("${PIPESTATUS[@]}")
unverified_theorem_suggestion_status=${unverified_theorem_suggestion_statuses[0]}
unverified_theorem_suggestion_json_status=${unverified_theorem_suggestion_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --suggest 8 "$ROOT_DIR/examples/theorem_suggestion_defaults.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["source"]["complete"] is True; assert [candidate["theorem"] for candidate in result["candidates"]] == ["safe_default"]; candidate = result["candidates"][0]; assert candidate["bindings"][1] == {"parameter": "amount", "value": {"kind": "int", "value": 7}}; assert candidate["applicable"] is True'
theorem_suggestion_default_statuses=("${PIPESTATUS[@]}")
theorem_suggestion_default_status=${theorem_suggestion_default_statuses[0]}
theorem_suggestion_default_json_status=${theorem_suggestion_default_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --suggest 4 "$ROOT_DIR/examples/theorem_suggestion_structured.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["status"] == "not_found"; assert result["source"]["admissible"] is False; assert result["candidates"] == []'
theorem_suggestion_structured_statuses=("${PIPESTATUS[@]}")
theorem_suggestion_structured_status=${theorem_suggestion_structured_statuses[0]}
theorem_suggestion_structured_json_status=${theorem_suggestion_structured_statuses[1]}
python3 - "$ROOT_DIR/build/elisa-proof" "$ROOT_DIR/examples/theorem_suggestions.elisa" <<'PY'
import subprocess, sys
first = subprocess.check_output([sys.argv[1], "--suggest", "4", sys.argv[2]])
second = subprocess.check_output([sys.argv[1], "--suggest", "4", sys.argv[2]])
assert first == second
PY
deterministic_theorem_suggestion_status=$?
"$ROOT_DIR/build/elisa-proof" --suggest 999999 "$ROOT_DIR/examples/theorem_suggestions.elisa" | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["status"] == "not_found"; assert result["goal_fingerprint"] is None; assert result["candidates"] == []'
missing_theorem_suggestion_statuses=("${PIPESTATUS[@]}")
missing_theorem_suggestion_status=${missing_theorem_suggestion_statuses[0]}
missing_theorem_suggestion_json_status=${missing_theorem_suggestion_statuses[1]}
set -e
if [[ "$checked_index_diagnostics_status" -ne 1 || "$checked_index_diagnostics_json_status" -ne 0 || "$multiple_preconditions_status" -ne 1 || "$multiple_preconditions_json_status" -ne 0 || "$lexicographic_repair_queue_status" -ne 0 || "$lexicographic_repair_queue_json_status" -ne 0 || "$void_postcondition_goal_status" -ne 1 || "$void_postcondition_goal_json_status" -ne 0 || "$focused_open_goal_status" -ne 0 || "$focused_open_goal_json_status" -ne 0 || "$focused_proved_goal_status" -ne 0 || "$focused_proved_goal_json_status" -ne 0 || "$focused_missing_goal_status" -ne 2 || "$focused_missing_goal_json_status" -ne 0 || "$focused_overflow_goal_status" -ne 2 || "$focused_negative_goal_status" -ne 2 || "$stable_goal_fingerprint_status" -ne 0 || "$theorem_catalog_status" -ne 0 || "$theorem_catalog_json_status" -ne 0 || "$lemma_summary_provenance_status" -ne 0 || "$lemma_summary_provenance_json_status" -ne 0 || "$rejected_theorem_catalog_status" -ne 1 || "$rejected_theorem_catalog_json_status" -ne 0 || "$default_theorem_catalog_status" -ne 0 || "$default_theorem_catalog_json_status" -ne 0 || "$stable_theorem_fingerprint_status" -ne 0 || "$theorem_suggestion_status" -ne 0 || "$theorem_suggestion_json_status" -ne 0 || "$unverified_theorem_suggestion_status" -ne 1 || "$unverified_theorem_suggestion_json_status" -ne 0 || "$theorem_suggestion_default_status" -ne 0 || "$theorem_suggestion_default_json_status" -ne 0 || "$theorem_suggestion_structured_status" -ne 2 || "$theorem_suggestion_structured_json_status" -ne 0 || "$deterministic_theorem_suggestion_status" -ne 0 || "$missing_theorem_suggestion_status" -ne 2 || "$missing_theorem_suggestion_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: goal/repair API statuses checked=%s preconditions=%s lexicographic=%s void=%s focused-open=%s focused-proved=%s focused-missing=%s overflow=%s negative=%s goal-fingerprint=%s theorem-catalog=%s lemma-provenance=%s rejected-catalog=%s defaults=%s theorem-fingerprint=%s suggestion=%s unverified-suggestion=%s default-suggestion=%s structured-suggestion=%s deterministic-suggestion=%s missing-suggestion=%s missing-suggestion-json=%s\n' \
        "$checked_index_diagnostics_status" "$multiple_preconditions_status" "$lexicographic_repair_queue_status" "$void_postcondition_goal_status" \
        "$focused_open_goal_status" "$focused_proved_goal_status" "$focused_missing_goal_status" "$focused_overflow_goal_status" "$focused_negative_goal_status" \
        "$stable_goal_fingerprint_status" "$theorem_catalog_status" "$lemma_summary_provenance_status" "$rejected_theorem_catalog_status" \
        "$default_theorem_catalog_status" "$stable_theorem_fingerprint_status" "$theorem_suggestion_status" "$unverified_theorem_suggestion_status" \
        "$theorem_suggestion_default_status" "$theorem_suggestion_structured_status" "$deterministic_theorem_suggestion_status" \
        "$missing_theorem_suggestion_status" "$missing_theorem_suggestion_json_status" >&2
    exit 1
fi

if [[ "$rejected_index_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_index_bounds=%s\n' "$rejected_index_bounds_status" >&2
    exit 1
fi

if [[ "$rejected_index_call_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_index_call=%s\n' "$rejected_index_call_status" >&2
    exit 1
fi

if [[ "$rejected_index_pure_result_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_index_pure_result=%s\n' "$rejected_index_pure_result_status" >&2
    exit 1
fi

if [[ "$rejected_fixed_array_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_fixed_array_bounds=%s\n' "$rejected_fixed_array_bounds_status" >&2
    exit 1
fi

if [[ "$rejected_fixed_array_slice_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_fixed_array_slice_bounds=%s\n' "$rejected_fixed_array_slice_bounds_status" >&2
    exit 1
fi

if [[ "$captured_structural_accumulator_status" -ne 0 ]]; then
    printf 'proof test matrix failed: captured_structural_accumulator=%s\n' "$captured_structural_accumulator_status" >&2
    exit 1
fi

if [[ "$rejected_slice_bounds_status" -ne 1 || "$rejected_field_alias_status" -ne 1 ]]; then
    printf 'proof test matrix failed: rejected_slice_bounds=%s rejected_field_alias=%s\n' "$rejected_slice_bounds_status" "$rejected_field_alias_status" >&2
    exit 1
fi

if [[ "$nested_frame_status" -ne 0 || "$indexed_frame_status" -ne 0 || "$rejected_nested_frame_status" -ne 1 || "$rejected_deep_frame_status" -ne 1 || "$rejected_indexed_frame_status" -ne 1 || "$counterexample_status" -ne 1 ]]; then
    printf 'proof test matrix failed: nested_frame=%s indexed_frame=%s rejected_nested_frame=%s rejected_deep_frame=%s rejected_indexed_frame=%s counterexample=%s\n' "$nested_frame_status" "$indexed_frame_status" "$rejected_nested_frame_status" "$rejected_deep_frame_status" "$rejected_indexed_frame_status" "$counterexample_status"
    exit 1
fi

if [[ "$modulo_division_bounds_status" -ne 0 || "$rejected_modulo_division_bounds_status" -ne 1 ]]; then
    printf 'proof test matrix failed: modulo_division_bounds=%s rejected_modulo_division_bounds=%s\n' "$modulo_division_bounds_status" "$rejected_modulo_division_bounds_status" >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_duplicate_quantifier.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed" and report["verification_state"] == "unsupported"; assert report["summary"]["semantic_errors"] == 0 and report["summary"]["obligations"] == 3; assert any(finding["kind"] == "contract-proposition-type" and finding["status"] == "unsupported" and finding["name"] == "duplicate_dictionary_binder" for finding in report["findings"]); assert not any(goal["rule"] == "quantifier-forall" for goal in report["goals"]); assert not any(certificate["rule"] == "quantifier-forall" for certificate in report["certificates"]); assert report["replay"]["certificates"] == report["replay"]["replayed"] == 1 and report["replay"]["gaps"] == 0; assert report["trust"]["trusted_assumptions"] == []'
duplicate_quantifier_statuses=("${PIPESTATUS[@]}")
duplicate_quantifier_status=${duplicate_quantifier_statuses[0]}
duplicate_quantifier_json_status=${duplicate_quantifier_statuses[1]}
set -e
if [[ "$duplicate_quantifier_status" -ne 1 || "$duplicate_quantifier_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: duplicate dictionary quantifier binder was not rejected cleanly (proof=%s json=%s)\n' "$duplicate_quantifier_status" "$duplicate_quantifier_json_status" >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["format"] == "elisa-proof-tactic-result-v1"; assert report["status"] == "proved"; assert report["source"]["fingerprint_match"] is True; assert report["tactic"]["certificate_replayed"] is True; assert report["tactic"]["kernel_trace_replayed"] is True; assert len(report["state"]["trace"]) == 2'
portable_script_status=${PIPESTATUS[0]}
if [[ "$portable_script_status" -ne 0 ]]; then
    printf 'proof test matrix failed: portable tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_branch.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["branch_certificate_replayed"] is True; assert report["branches"]["left"]["solved"] and report["branches"]["right"]["solved"]'
portable_branch_status=${PIPESTATUS[0]}
if [[ "$portable_branch_status" -ne 0 ]]; then
    printf 'proof test matrix failed: portable branch tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_branch.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["branch_certificate_replayed"] is True; assert report["branches"]["left"]["branches"]["left"]["solved"] is True; assert report["branches"]["left"]["branches"]["right"]["solved"] is True'
portable_nested_branch_status=${PIPESTATUS[0]}
if [[ "$portable_nested_branch_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested portable branch tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_cases.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["branch_certificate_replayed"] is True; assert report["branches"]["left"]["trace"][-1]["action"] == "cases"; assert report["branches"]["left"]["branches"]["left"]["facts"] == [{"kind": "bool", "value": True}]'
portable_nested_cases_status=${PIPESTATUS[0]}
if [[ "$portable_nested_cases_status" -ne 0 ]]; then
    printf 'proof test matrix failed: nested portable cases tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target_nested_branch.json" "$ROOT_DIR/examples/verified_branch.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert binding["bound"] and binding["goal_id"] == 1 and binding["previously_proven"]; assert binding["fingerprint_match"] is True; assert report["tactic"]["certificate_replayed"] is True; assert report["branches"]["left"]["branches"]["right"]["solved"] is True'
source_nested_branch_status=${PIPESTATUS[0]}
if [[ "$source_nested_branch_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound nested branch tactic script\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert binding["bound"] and binding["goal_id"] == 7 and binding["previously_proven"]; assert binding["fingerprint_match"] is True; assert report["tactic"]["status"] == "proved"; assert len(report["state"]["initial_facts"]) == 3; assert any(fact["kind"] == "call" and fact["callee"]["name"] == "__elisa_primitive_scalar_type" for fact in report["state"]["initial_facts"]); assert any(fact["kind"] == "call" and fact["callee"]["name"] == "__elisa_signed_type_bound" for fact in report["state"]["initial_facts"])'
source_bound_script_status=${PIPESTATUS[0]}
if [[ "$source_bound_script_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound tactic script\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_source_bound_struct_rewrite.json" "$ROOT_DIR/examples/rejected_congruence.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["source_goal_binding"]["goal_id"] == 14; assert report["tactic"]["valid"] is False; assert report["tactic"]["certificate_replayed"] is False; assert report["state"]["trace"][0]["accepted"] is False; assert "primitive-scalar" in report["state"]["trace"][0]["reason"]'
source_bound_struct_rewrite_statuses=("${PIPESTATUS[@]}")
source_bound_struct_rewrite_status=${source_bound_struct_rewrite_statuses[0]}
source_bound_struct_rewrite_json_status=${source_bound_struct_rewrite_statuses[1]}
set -e
if [[ "$source_bound_struct_rewrite_status" -ne 1 || "$source_bound_struct_rewrite_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound rewrite used overloaded struct equality (proof=%s json=%s)\n' "$source_bound_struct_rewrite_status" "$source_bound_struct_rewrite_json_status" >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert report["admission_scope"] == "target"; assert report["source"]["status"] == "failed"; assert report["source"]["complete"] is False; assert report["source"]["admissible"] is True; assert binding["bound"] and binding["goal_id"] == 1 and not binding["previously_proven"]; assert binding["goal_fingerprint"]["value"] == 2903951783 and binding["fingerprint_match"] is True; assert report["tactic"]["certificate_replayed"] is True; assert any(fact["kind"] == "call" and not fact.get("argument_names") for fact in report["state"]["initial_facts"])'
repair_target_status=${PIPESTATUS[0]}
if [[ "$repair_target_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-bound tactic could not repair an open target\n' >&2
    exit 1
fi

"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target_shifted.json" "$ROOT_DIR/examples/tactic_repair_target_shifted.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "proved"; assert binding["goal_id"] == 2; assert binding["goal_fingerprint"]["value"] == 2903951783; assert binding["fingerprint_match"] is True'
shifted_repair_target_status=${PIPESTATUS[0]}
if [[ "$shifted_repair_target_status" -ne 0 ]]; then
    printf 'proof test matrix failed: stable target proof did not survive unrelated source insertion\n' >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target_stale_goal.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["source_goal_binding"]["fingerprint_match"] is False; assert report["tactic"]["valid"] is False; assert "goal_fingerprint" in report["tactic"]["reason"]'
stale_repair_target_statuses=("${PIPESTATUS[@]}")
stale_repair_target_status=${stale_repair_target_statuses[0]}
stale_repair_target_json_status=${stale_repair_target_statuses[1]}
set -e
if [[ "$stale_repair_target_status" -ne 1 || "$stale_repair_target_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: stale target goal fingerprint was not refused cleanly (proof=%s json=%s)\n' "$stale_repair_target_status" "$stale_repair_target_json_status" >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target.json" "$ROOT_DIR/examples/rejected_tactic_repair_semantic.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["source"]["complete"] is False; assert report["source"]["admissible"] is False; assert report["tactic"]["certificate_replayed"] is True'
semantic_repair_statuses=("${PIPESTATUS[@]}")
semantic_repair_status=${semantic_repair_statuses[0]}
semantic_repair_json_status=${semantic_repair_statuses[1]}
set -e
if [[ "$semantic_repair_status" -ne 1 || "$semantic_repair_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: target tactic did not report the semantic source error cleanly (proof=%s json=%s)\n' "$semantic_repair_status" "$semantic_repair_json_status" >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/examples/rejected_tactic_repair_proposition_type.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert any(finding["kind"] == "contract-proposition-type" and finding["name"] == "rejected_nonboolean_ensure" for finding in report["findings"])'
proposition_source_statuses=("${PIPESTATUS[@]}")
proposition_source_status=${proposition_source_statuses[0]}
proposition_source_json_status=${proposition_source_statuses[1]}
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target.json" "$ROOT_DIR/examples/rejected_tactic_repair_proposition_type.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); binding = report["source_goal_binding"]; assert report["status"] == "failed"; assert report["source"]["admissible"] is False; assert binding["bound"] and binding["goal_id"] == 1 and binding["fingerprint_match"] is True; assert report["tactic"]["valid"] is True and report["tactic"]["certificate_replayed"] is True'
proposition_tactic_statuses=("${PIPESTATUS[@]}")
proposition_tactic_status=${proposition_tactic_statuses[0]}
proposition_tactic_json_status=${proposition_tactic_statuses[1]}
set -e
if [[ "$proposition_source_status" -ne 1 || "$proposition_source_json_status" -ne 0 || "$proposition_tactic_status" -ne 1 || "$proposition_tactic_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a valid target tactic laundered an ill-typed source contract (source=%s/%s tactic=%s/%s)\n' \
        "$proposition_source_status" "$proposition_source_json_status" "$proposition_tactic_status" "$proposition_tactic_json_status" >&2
    exit 1
fi

set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_forged_resource_target.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["source_goal_binding"]["goal_id"] == 0; assert report["tactic"]["valid"] is False; assert report["tactic"]["certificate_replayed"] is False'
resource_target_statuses=("${PIPESTATUS[@]}")
resource_target_status=${resource_target_statuses[0]}
resource_target_json_status=${resource_target_statuses[1]}
set -e
if [[ "$resource_target_status" -ne 1 || "$resource_target_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: proposition tactic did not refuse resource-certificate replacement cleanly (proof=%s json=%s)\n' "$resource_target_status" "$resource_target_json_status" >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_borrow_after_move.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert any(finding["kind"] == "resource-use-after-move" and finding["message"] == "a borrow cannot be created from a moved resource binding" and finding["status"] == "disproved" for finding in report["findings"]); assert report["replay"]["gaps"] == 0'
rejected_borrow_after_move_probe_statuses=("${PIPESTATUS[@]}")
rejected_borrow_after_move_probe_status=${rejected_borrow_after_move_probe_statuses[0]}
rejected_borrow_after_move_json_status=${rejected_borrow_after_move_probe_statuses[1]}
set -e
if [[ "$rejected_borrow_after_move_probe_status" -ne 1 || "$rejected_borrow_after_move_json_status" -ne 0 ]]; then
    printf 'proof test matrix failed: borrow-after-move was not rejected with replayable evidence (proof=%s json=%s)\n' "$rejected_borrow_after_move_probe_status" "$rejected_borrow_after_move_json_status" >&2
    exit 1
fi

run_json_report "$ROOT_DIR/examples/congruence.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; assert report["findings"] == []; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"congruence_sum", "congruence_difference", "congruence_product", "congruence_nested", "congruence_chain", "congruence_boolean", "congruence_bitwise", "congruence_conditional", "congruence_character", "congruence_boolean_parameters", "congruence_bounded_unsigned", "congruence_pure_call_result", "congruence_opaque_locals"} <= names'
congruence_status=${PIPESTATUS[1]}
if [[ "$congruence_status" -ne 0 ]]; then
    printf 'proof test matrix failed: ground congruence closure did not carry equalities through deterministic formers\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_congruence.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"disequality_premise", "order_premise", "disjunctive_premise", "unrelated_operand", "distinct_former", "struct_equality_premise", "local_struct_equality_premise", "constructed_aggregate", "call_congruence", "cross_width", "wrapping_operand"}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}; assert not (refused & claimed); assert refused <= {finding["name"] for finding in report["findings"]}; assert "indexed_element" in claimed'
rejected_congruence_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_congruence_status" -ne 0 ]]; then
    printf 'proof test matrix failed: congruence admitted a goal outside the deterministic term fragment\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_reflexivity.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"reflexive_equality", "reflexive_order", "reflexive_reverse_order", "symmetric_equality", "local_reflexive_equality", "field_reflexive_equality", "field_reflexive_order", "element_reflexive_equality", "opaque_call_reflexive_equality", "struct_element_binder_reflexive_equality"}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety"}; assert not (refused & claimed); assert refused <= {finding["name"] for finding in report["findings"]}'
rejected_reflexivity_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_reflexivity_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a user-defined equality was assumed reflexive, symmetric, or coherent with ordering\n' >&2
    exit 1
fi

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

# A fact over a by-value scalar the body never lets escape survives an opaque call, and a
# conjunctive guard entails each of its parts. Both are needed to re-establish a bounded-recursion
# precondition at a second call; each conjunct is a derived fact the kernel re-proves.
set +e
run_json_report "$ROOT_DIR/examples/call_stable_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"survives_state_writing_call", "survives_second_call", "survives_branch_join", "survives_call_guard", "survives_returning_branch"} <= names; origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}; assert "branch-conjunct" in origins'
call_stable_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$call_stable_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: call-stable facts and branch conjuncts\n' >&2
    exit 1
fi

# The boundary of those two rules: a scalar the callee can write, a scalar a branch assigns, and a
# disjunction are all refused. Nothing here may be proven.
set +e
run_json_report "$ROOT_DIR/examples/rejected_call_stable_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"aliased_scalar", "assigned_in_branch", "disjunctive_branch", "negated_conjunctive_guard", "rebound_after_guard"}; assert refused <= {finding["name"] for finding in report["findings"]}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety" and goal["name"] in refused and "depth <= 127" in str(goal)}; assert not claimed'
rejected_call_stable_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_call_stable_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fact survived a call or a branch that could falsify it\n' >&2
    exit 1
fi

# A by-value aggregate that contains a reference still reaches external state. Its nested
# collection extent must be forgotten across a call that can mutate the referent through a global.
set +e
run_json_report "$ROOT_DIR/examples/rejected_nested_shared_extent_global.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {item["name"]: item for item in report["declaration_details"] if item["kind"] == "function"}; assert not functions["nested_shared_extent_must_not_survive"]["verified"]; assert any(item["kind"] == "index-upper-unproven" and item["name"] == "nested_shared_extent_must_not_survive" and item["status"] == "unknown" for item in report["findings"]); assert not any(goal["name"] == "nested_shared_extent_must_not_survive" and goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"])'
rejected_nested_shared_extent_global_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_nested_shared_extent_global_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a by-value aggregate reference preserved a mutable pointee extent across a call\n' >&2
    exit 1
fi

# A view-bearing aggregate is borrowed storage too, even though `view[T]` is not itself a
# reference field. Refuse to preserve even a nested field fact through a call until that alias
# shape can be modeled path-sensitively.
set +e
run_json_report "$ROOT_DIR/examples/rejected_borrowed_view_call_stability.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {item["name"]: item for item in report["declaration_details"] if item["kind"] == "function"}; assert not functions["borrowed_view_root_must_not_preserve_nested_facts"]["verified"]; assert any(item["kind"] == "ensure-unproven" and item["name"] == "borrowed_view_root_must_not_preserve_nested_facts" and item["status"] == "unknown" for item in report["findings"]); assert not any(goal["name"] == "borrowed_view_root_must_not_preserve_nested_facts" and goal["rule"] != "resource-safety" and goal["proven"] for goal in report["goals"])'
rejected_borrowed_view_call_stability_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_borrowed_view_call_stability_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a view-bearing aggregate was trusted as call-local storage\n' >&2
    exit 1
fi

# A call that lends only shared references cannot change the caller's resource state, so it is
# admitted from the callee's declared modes with no body summary. That is the only path open to a
# recursive component, which can never consume one of its own summaries.
set +e
run_json_report "$ROOT_DIR/examples/shared_borrow_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; kinds = {node["kind"] for node in nodes}; assert "resource-call-lend" in kinds; shared = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert all(node["left"] == 0 and node["children_count"] == node["auxiliary"] * 2 for node in shared); formals = [nodes[child] for node in shared for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]; assert formals; assert all(formal["kind"] == "resource-call-formal" for formal in formals); assert all(formal["operator"] in ("value", "external-shared") for formal in formals); assert any(formal["operator"] == "external-shared" for formal in formals)'
shared_borrow_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$shared_borrow_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: shared-reference calls\n' >&2
    exit 1
fi

# A capability the callee may write through, one that outlives the call, and one the caller no
# longer holds all still require the callee's own converged summary.
set +e
run_json_report "$ROOT_DIR/examples/rejected_shared_borrow_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "recursive_reference_return") in findings; assert ("resource-use-after-move", "lends_moved_value") in findings; assert ("borrow-call-opaque", "lends_shared_while_mutably_borrowed") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_shared_borrow_calls_status=${PIPESTATUS[1]}
set -e
# An exclusive lend needs no callee summary either: the callee can do no more than write through
# the reference, so the caller over-approximates the call by a write to the whole lent place. Every
# exclusive capability must be one the caller holds alone.
set +e
run_json_report "$ROOT_DIR/examples/writable_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; lends = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert lends; formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]; assert any(formal["operator"] == "external-mutable" for formal in formals); assert any(formal["operator"] == "external-shared" for formal in formals)'
writable_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$writable_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: confined writable lending\n' >&2
    exit 1
fi

# Signature types resolve across every block of a module, so an `extend` block's recursive
# shared walk returning a sibling-declared scalar struct is a confined lend, while a sibling
# struct that holds a reference still requires the callee's converged summary.
set +e
run_json_report "$ROOT_DIR/examples/module_extend_shared_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
module_extend_lend_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_module_extend_shared_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "extend_escape") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_module_extend_lend_status=${PIPESTATUS[1]}
set -e
if [[ "$module_extend_lend_status" -ne 0 || "$rejected_module_extend_lend_status" -ne 0 ]]; then
    printf 'proof test matrix failed: module extend lend types\n' >&2
    exit 1
fi

# A module constant passed by value is spelled by its module path in the resource trace, which
# replay admits as static. A bare constant is qualified by the producer, also from an `extend`
# block; a local that shadows it stays a bare binding.
set +e
run_json_report "$ROOT_DIR/examples/replay_qualified_constant_argument.elisa" | python3 -c '
import json, sys
report = json.load(sys.stdin)
assert report["status"] == "proved" and report["replay"]["gaps"] == 0
nodes = report["kernel"]["nodes"]
def spell(index):
    node = nodes[index]
    if node["kind"] == "scope":
        return spell(node["left"]) + "::" + node["name"]
    return node["name"] if node["kind"] == "ident" else node["kind"]
spelled = [spell(node["left"]) for node in nodes if node["kind"] == "resource-call-arg" and node["name"] == "remaining"]
assert spelled == ["binary", "Limits::DEPTH", "QualifiedArgument::LOCAL_DEPTH", "absent::ROOT_DEPTH", "LOCAL_DEPTH", "QualifiedArgument::LOCAL_DEPTH"], spelled
'
qualified_constant_status=${PIPESTATUS[1]}
set -e
if [[ "$qualified_constant_status" -ne 0 ]]; then
    printf 'proof test matrix failed: static constant spelling in resource traces\n' >&2
    exit 1
fi

# Two exclusive capabilities over one place, a shared one beside an exclusive one, and an
# exclusive lend across a live borrow are each refused with no event recorded. The pinned
# frontend also reports the two call-site overlaps; the proof checker must refuse all three on
# its own, including the live-borrow case the frontend does not see.
set +e
run_json_report "$ROOT_DIR/examples/rejected_writable_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert sorted((diagnostic["line"], diagnostic["actual"]) for diagnostic in report["semantic_diagnostics"]) == [(16, "swap_pair"), (35, "read_and_write")]; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "swap_pair") in findings; assert ("borrow-call-opaque", "read_and_write") in findings; assert ("borrow-call-opaque", "touch_borrowed") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_writable_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_writable_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unconfined exclusive lend was admitted\n' >&2
    exit 1
fi

# A lifetime parameter does not stop a call from being a lend: the callee may allocate into a
# mapped caller region and can never close one. Every formal lifetime must be pinned to a region
# active at the call, and every region-carrying actual must land on a formal declaring it.
set +e
run_json_report "$ROOT_DIR/examples/region_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; lends = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert lends; assert all(node["children_count"] == node["auxiliary"] * 2 + node["right"] for node in lends); assert any(node["right"] == 2 for node in lends); maps = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"] * 2:node["children_start"] + node["children_count"]]]; assert maps; assert all(entry["kind"] == "resource-call-region" and entry["operator"] == "param" and entry["name"] and entry["secondary_name"] for entry in maps); formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["auxiliary"] * 2]]; assert any(formal["secondary_name"] for formal in formals)'
region_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$region_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic lending\n' >&2
    exit 1
fi

# A region-polymorphic callee that does have a converged summary must compose into its caller. A
# construction's left edge is the constructed type, not a value; a record update's left edge is
# the base record and still is one.
set +e
run_json_report "$ROOT_DIR/examples/region_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert {"resource-region-alloc", "construct", "record-update", "resource-call"} <= kinds'
region_call_summary_status=${PIPESTATUS[1]}
set -e
if [[ "$region_call_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic callee summary composition\n' >&2
    exit 1
fi

# A branch condition may carry an executable call wherever that call runs whenever the condition
# is evaluated, not only at the root. A call that may be skipped stays refused.
set +e
run_json_report "$ROOT_DIR/examples/condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"bare_call", "negated_call", "compared_call", "short_circuit_left", "arithmetic_call", "guarded_index"} <= names'
condition_call_positions_status=${PIPESTATUS[1]}
set -e
if [[ "$condition_call_positions_status" -ne 0 ]]; then
    printf 'proof test matrix failed: executable calls in branch conditions\n' >&2
    exit 1
fi

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
run_json_report "$ROOT_DIR/examples/rejected_u64_max_conflict.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed" and report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}; assert not functions["u64_max_does_not_imply_zero"]["verified"]; assert not functions["usize_max_does_not_imply_zero"]["verified"]; assert functions["u64_reflexive_equality_remains_provable"]["verified"]; assert not functions["u64_max_is_not_less_than_zero"]["verified"]; assert not functions["usize_global_max_is_not_negative"]["verified"]; assert not functions["usize_local_max_is_not_negative"]["verified"]; assert not functions["u8_overflow_is_not_unequal"]["verified"]; assert not functions["u8_shift_outside_width_is_not_zero"]["verified"]; assert not functions["u8_overflow_hidden_in_conditional_is_not_nonzero"]["verified"]; refused = {f["name"]: f for f in report["findings"] if f["kind"] == "ensure-unproven"}; assert {"u64_max_does_not_imply_zero", "usize_max_does_not_imply_zero", "u64_max_is_not_less_than_zero", "usize_global_max_is_not_negative", "u8_overflow_is_not_unequal", "u8_shift_outside_width_is_not_zero", "u8_overflow_hidden_in_conditional_is_not_nonzero"} <= {name for name, finding in refused.items() if finding["status"] == "unknown"}; assert refused["usize_local_max_is_not_negative"]["status"] == "unknown" and not refused["usize_local_max_is_not_negative"]["counterexample_found"] and refused["usize_local_max_is_not_negative"]["counterexample"] == []'
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
