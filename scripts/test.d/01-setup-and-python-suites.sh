# shellcheck shell=bash
# Part 1 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
python3 "$ROOT_DIR/scripts/check_source_length.py"
python3 "$ROOT_DIR/scripts/test_keep_going.py"
python3 "$ROOT_DIR/scripts/test_clang_resolution.py"
python3 "$ROOT_DIR/scripts/test_compiler_selection.py"
python3 "$ROOT_DIR/test/audit_harness_test.py"
# ELISA_PROOF_SKIP_BUILD=1 tests prebuilt binaries (for example on a remote runner).
if [[ "${ELISA_PROOF_SKIP_BUILD:-0}" != "1" ]]; then
    # The portable package checker is its own small product built from the same snapshot; both
    # products build in one call, compiling side by side.
    ELISA_PROOF_PRODUCTS=all "$ROOT_DIR/scripts/build.sh"
else
    # Prebuilt binaries still need build/snapshot: the standalone compile probes read the
    # frontend export and the examples from it. Exporting compiles nothing.
    (
        # shellcheck source=scripts/compiler_snapshot.sh
        source "$ROOT_DIR/scripts/compiler_snapshot.sh"
    )
fi

# ELISA_PROOF_JOBS>1 runs every literal run_json_report fixture in parallel first; the serial
# assertions below then read those stored reports (scripts/prefetch_reports.py).
# A preset ELISA_PROOF_REPORT_CACHE (filled by scripts/remote/farm.sh on hosts with this same
# checkout path) is used as is, with no local prefetch.
REPORT_CACHE="${ELISA_PROOF_REPORT_CACHE:-}"
REPORT_PREFETCH_PID=""
if [[ -n "$REPORT_CACHE" ]]; then
    export ELISA_PROOF_REPORT_CACHE="$REPORT_CACHE"
elif [[ "${ELISA_PROOF_JOBS:-1}" -gt 1 ]]; then
    REPORT_CACHE="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-reports.XXXXXX")"
    TEST_CLEANUP+=("$REPORT_CACHE")
    python3 "$ROOT_DIR/scripts/prefetch_reports.py" "$ROOT_DIR/scripts/test.sh" "$ROOT_DIR/build/elisa-proof" "$REPORT_CACHE" "$ROOT_DIR" "$(( ELISA_PROOF_JOBS > 2 ? ELISA_PROOF_JOBS - 1 : ELISA_PROOF_JOBS ))" &
    REPORT_PREFETCH_PID=$!
    export ELISA_PROOF_REPORT_CACHE="$REPORT_CACHE" ELISA_PROOF_JOBS
fi

# The marker-decoder regression must finish under the normal watchdog; under ELISA_PROOF_JOBS it
# holds a heavy-fixture slot so the prefetch cannot starve it of memory. Completion
# is not proof: unresolved obligations remain visible in the report.
if ! ELISA_FULL_AUDIT_SOURCE="$ROOT_DIR/test/repro/audit_unsigned_marker.elisa" \
    ELISA_FULL_AUDIT_BINARY="$ROOT_DIR/build/elisa-proof" \
    python3 "$ROOT_DIR/scripts/report_cache.py" --slot "$ROOT_DIR/test/repro/audit_unsigned_marker.elisa" -- "$ROOT_DIR/scripts/audit_full_source.sh" | python3 -c 'import json, sys; audit=json.load(sys.stdin); assert audit["complete"]; assert audit["replay_gaps"] == 0'; then
    printf 'proof test matrix failed: unsigned-marker audit did not complete with clean replay\n' >&2
    exit 1
fi

# Run one scripts/test_*.py, reading its prefetched output when ELISA_PROOF_JOBS>1 stored one.
run_py_test() {
    local name="$1" entry=""
    if [[ -n "$REPORT_CACHE" ]]; then
        entry="$REPORT_CACHE/py-$name"
        while [[ ! -f "$entry.rc" ]] && [[ -n "$REPORT_PREFETCH_PID" ]] && kill -0 "$REPORT_PREFETCH_PID" 2>/dev/null; do
            sleep 1  # poll-ok: local file from our own prefetcher
        done
    fi
    if [[ -n "$entry" && -f "$entry.rc" ]]; then
        cat "$entry.out"
        return "$(cat "$entry.rc")"
    fi
    python3 "$ROOT_DIR/scripts/$name"
}
run_py_test test_report_cache_identity.py
run_py_test test_report_cache_real_equivalence.py
run_py_test test_report_cache_executable_swap.py
run_py_test test_report_cache_missing_nested_dependency.py
run_py_test test_report_cache_nested_dependency_edit.py
run_py_test test_report_cache_symlink_dependency.py
run_py_test test_p01_baseline.py
run_py_test test_bounded_model_work_budget.py
run_py_test tests/test_perf_luna_corpus_manifest.py
run_py_test test_r013_logical_work_stress.py
run_py_test test_disjunction_call_domain_replay_gate.py
run_py_test test_disjunction_search_bounds.py
run_py_test test_p05_package_restart.py
run_py_test test_conditional_ensure_replay_gap.py
run_py_test test_declaration_artifact_identity.py
run_py_test test_declaration_artifact_concurrency.py
run_py_test tests/test_soundness_incident_registry.py
run_py_test test_p07_support_census.py
run_py_test tests/test_scalar_witness_name_index.py
run_py_test remote/test_object_cache_key.py
run_py_test test_build_dependency_closure.py
run_py_test test_build_manifest_sidecar_integrity.py
run_py_test test_compiler_recipe_inputs.py
run_py_test test_plain_enum_propositions.py
run_py_test test_conditional_scaled_sum.py
run_py_test test_guarded_call_result.py
run_py_test test_range_binder_resources.py
run_py_test test_admission_invariant_diagnostics.py
run_py_test test_frame_source_cli.py
run_py_test test_frame_call_cli.py
run_py_test test_source_call_result_alias.py
run_py_test test_stable_conditional_predicates.py
run_py_test test_literal_quotient_denial.py
run_py_test test_captured_initializer_entry.py
run_py_test test_mutable_for_entry.py
run_py_test test_for_saturation_replay.py
run_py_test test_local_digit_decimal.py
run_py_test test_record_fixed_arrays.py
run_py_test test_qualified_block_ranges.py
run_py_test test_float_integer_bounds.py
run_py_test test_scalar_field_priority.py
run_py_test test_float_scalar_resources.py
run_py_test test_float_call_result_shape.py
run_py_test test_fixed_index_admission.py
run_py_test test_operator_witness_snapshot_budget.py
run_py_test test_local_record_fixed_index.py
run_py_test test_plain_enum_resource_call.py
run_py_test test_indexed_scalar_snapshot.py
run_py_test test_captured_loop_entry.py
run_py_test test_search_break_replay.py
run_py_test test_mixed_record_search.py
run_py_test test_value_block_assignment.py
run_py_test test_block_result_bounds.py
run_py_test test_portable_frame.py
run_py_test test_build_source_snapshot_race.py
run_py_test test_compiler_snapshot_preserves_files.py
run_py_test test_cycle_arena_runtime_rejection.py
run_py_test tests/test_json_result_lattice.py

# Buffer JSON probes so a valid-looking report cannot hide a crash or an exit/verdict mismatch.
# `proved_with_replay_gaps` is a valid, incomplete report state—not malformed JSON—and, like
# `failed`, is explicitly non-successful. Preserve that lattice state for downstream assertions.
run_json_report() {
    local source_path="$1"
    local report_path
    local proof_status
    local expected_status

    if ! report_path="$(mktemp "${TMPDIR:-/tmp}/elisa-proof-json-probe.XXXXXX")"; then
        printf 'proof test matrix failed: could not allocate a report buffer for %s\n' "$source_path" >&2
        return 98
    fi
    local cache_key=""
    if [[ -n "$REPORT_CACHE" ]]; then
        cache_key="$REPORT_CACHE/$(python3 "$ROOT_DIR/scripts/report_cache.py" --key "$source_path" "$ROOT_DIR/build/elisa-proof")"
        # Wait for a prefetched fixture's entry while the prefetcher still runs.
        while [[ ! -f "$cache_key.rc" ]] && [[ -n "$REPORT_PREFETCH_PID" ]] && kill -0 "$REPORT_PREFETCH_PID" 2>/dev/null; do
            sleep 1  # poll-ok: local file from our own prefetcher
            grep -qF "\"\$ROOT_DIR/${source_path#"$ROOT_DIR/"}\"" "$ROOT_DIR/scripts/test.sh" || break
        done
    fi
    if [[ -n "$cache_key" && -f "$cache_key.rc" ]]; then
        cp "$cache_key.json" "$report_path"
        proof_status="$(cat "$cache_key.rc")"
    elif "$ROOT_DIR/build/elisa-proof" --json "$source_path" >"$report_path"; then
        proof_status=0
    else
        proof_status=$?
    fi
    if ! expected_status="$(python3 "$ROOT_DIR/scripts/report_exit_status.py" "$report_path")"; then
        printf 'proof test matrix failed: could not classify verifier JSON result for %s (exit=%s)\n' "$source_path" "$proof_status" >&2
        rm -f "$report_path"
        return 98
    fi
    if [[ "$proof_status" -ne "$expected_status" ]]; then
        printf 'proof test matrix failed: verifier exit/report mismatch for %s (exit=%s verdict-exit=%s)\n' "$source_path" "$proof_status" "$expected_status" >&2
        rm -f "$report_path"
        return 97
    fi
    if ! cat "$report_path"; then
        printf 'proof test matrix failed: could not forward the complete JSON report for %s\n' "$source_path" >&2
        rm -f "$report_path"
        return 99
    fi
    rm -f "$report_path"
    return "$expected_status"
}

# A shadowed local has its inner type only within the branch/loop; the parameter's
# source-backed view and type must remain valid after each nested scope closes.
run_json_report "$ROOT_DIR/examples/source_context_scope.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["obligations"] > 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0; assert report["replay"]["gaps"] == 0'

# Missing lifetime/place information is unsupported, not a demonstrated violation.
run_py_test test_overlap_diagnostics.py
run_py_test test_certificate_reuse.py
run_py_test test_measurements.py
run_py_test tests/test_disjunction_work_accounting.py
run_py_test test_source_admission_matrix.py
run_py_test test_negated_conjunction_fallthrough.py
run_py_test test_or_chain_loop_update.py
run_py_test test_correlated_disjunction.py
run_py_test tests/test_correlated_disjunction_consumer_resolution.py
run_py_test test_closed_width_formulas.py
run_py_test test_parameter_heavy_return_analysis.py
run_py_test test_numeric_cast_operator.py
run_py_test test_rejected_numeric_cast_operator.py
run_py_test test_widening_cast.py
run_py_test test_cast_dispatch_soundness.py
run_py_test test_call_result_width.py
run_py_test test_adt_library.py
run_py_test test_adt_parser.py
run_py_test test_match_refuted_arms.py
run_py_test test_match_exhaustiveness.py
run_py_test test_chained_pure_calls.py
run_py_test test_pure_postcondition_calls.py
run_py_test test_pure_contract_summary_replay.py
run_py_test test_dispatcher_budget.py
run_py_test test_qualified_constants.py
run_py_test test_variant_exclusion.py
run_py_test test_signed_upper_bound.py
run_py_test test_refusal_gate.py
run_py_test test_report_count_semantics.py
run_py_test test_agent_protocol_schema.py
run_py_test test_deterministic_call_chain.py
run_py_test test_deterministic_operator_global.py
run_py_test test_tuple_field_region.py
run_py_test test_enum_tag_equality.py
run_py_test test_signed_local_field_bounds.py
run_py_test test_signed_tuple_label_bounds.py
run_py_test test_usize_increment_under_count.py
run_py_test test_disequality_strictness.py
run_py_test test_or_chains.py
run_py_test test_quantifier_oracle.py
run_py_test test_guard_and_flag_facts.py
run_py_test test_bool_local_branch_fact.py
run_py_test test_min_max_abs_summaries.py
run_py_test test_literal_count.py
run_py_test test_engine_state.py
run_py_test test_explain.py
run_py_test test_long_difference_chain.py
run_py_test test_can_block_frame.py
run_py_test test_collection_push_count.py
run_py_test test_collection_pop.py
run_py_test test_collection_pop_value.py
run_py_test test_census_diff.py
run_py_test test_refusal_census.py
run_py_test test_body_ensures.py
run_py_test test_contract_placement.py
run_py_test test_scalar_reference_index.py
run_py_test test_old_mutable_reference.py
run_py_test test_internal_marker_names.py
run_py_test test_unsigned_disjunction.py
run_py_test test_numeric_cast_contract.py
run_py_test test_source_map.py
run_py_test test_unsigned_distinct_constants.py
run_py_test test_unsigned_resource_source_policy.py
run_py_test test_fixed_array_constant_indices.py
run_py_test test_fixed_count_projection.py
run_py_test test_field_copy_next_write.py
run_py_test test_return_branch_path_fact.py
run_py_test test_kernel_inventory.py
run_py_test test_portable_trust_inventory.py
run_py_test test_unsigned_subtraction_upper.py
run_py_test test_unsigned_or_goal.py
run_py_test test_unsigned_sum_upper_shape.py
run_py_test test_unsigned_remainder_range.py
run_py_test test_unsigned_division_bounds.py
run_py_test test_signed_division_boundaries.py
run_py_test test_unsigned_u8_shift_boundaries.py
run_py_test test_loop_readonly_outer_index.py
run_py_test test_loop_state_joins.py
run_py_test test_captured_loop_constants.py
run_py_test test_for_identity_update.py
run_py_test test_for_alias_update.py
run_py_test test_scoped_summary_alias.py
run_py_test test_invariant_for_retention.py
run_py_test test_captured_search_entry.py
run_py_test test_value_block_effect_retention.py
run_py_test test_pure_range_search.py
run_py_test test_region_outer_facts.py
run_py_test test_conditional_fixed_extent.py
run_py_test test_branch_local_loop_atom.py
run_py_test test_private_value_declaration.py
run_py_test test_reference_free_enum_summary.py
run_py_test test_source_binding_harness_includes.py
run_py_test test_literal_call_partial_requires.py
run_py_test test_signed_product_growth.py
run_py_test test_same_module_call_replay.py
run_py_test test_indexed_boolean_denial.py
run_py_test test_counterexample_domains.py
run_py_test test_build_runtime_inputs.py
run_py_test test_ranking_context.py
run_py_test test_comprehension_resources.py
run_py_test test_monotone_orders.py
run_py_test test_replay_construct_arguments.py
run_py_test test_negated_guard_orders.py
run_py_test test_nested_early_return_guards.py
python3 "$ROOT_DIR/scripts/tests/test_portable_replay_generation_resolution.py"
python3 "$ROOT_DIR/scripts/tests/test_dogfood_package_pair_resolution.py"
run_py_test test_portable_source_metadata_trust.py
python3 "$ROOT_DIR/scripts/tests/test_portable_trust_projection.py"
run_py_test tests/test_package_mutation_campaign.py
run_py_test test_portable_replay.py
python3 "$ROOT_DIR/scripts/tests/test_portable_package_byte_boundaries.py"
python3 "$ROOT_DIR/scripts/tests/test_portable_package_json_scan_boundaries.py"
python3 "$ROOT_DIR/scripts/tests/test_portable_package_string_budget.py"
python3 "$ROOT_DIR/scripts/tests/test_portable_package_theorem_budget.py"
python3 "$ROOT_DIR/scripts/tests/test_perf_luna_benchmark.py"
python3 "$ROOT_DIR/scripts/tests/test_perf_luna_benchmark_hardening.py"
python3 "$ROOT_DIR/scripts/perf_luna_benchmark.py" --self-test
run_py_test test_resource_projection_e144_coverage.py
run_py_test test_resource_projection_harness.py
run_py_test test_inferred_tuple_summary.py
run_py_test test_tuple_callee_shadow.py
run_py_test test_alias_boundary_regression.py
run_py_test test_conjunction_denial.py
run_py_test test_linear_certificates.py
run_py_test test_smt_oracle.py
run_py_test test_symbolic_quantifiers.py
run_py_test test_indexed_write_frame.py
run_py_test test_byref_frame_forwarding.py
run_py_test test_collection_frames.py
run_py_test test_loop_exit_frame.py
run_py_test test_near_miss.py
run_py_test test_pure_unfolding.py
run_py_test test_struct_invariants.py
run_py_test test_correspondence_partial_coverage.py
run_py_test test_correspondence.py
run_py_test test_tactic_branch_regions.py
run_py_test test_vector_index_arithmetic.py
run_py_test test_adt_recursive_payload.py
run_py_test test_call_sum_premise.py
run_py_test test_nested_conditional_split.py
run_py_test test_conditional_result_branchwise.py
run_py_test test_goal_disjunct_split.py
run_py_test test_include_constant_scope.py
run_py_test test_include_function_scope.py
run_py_test test_replay_dependency_row.py
python3 "$ROOT_DIR/scripts/tests/test_deterministic_call_qualified_replay.py"
python3 "$ROOT_DIR/scripts/tests/test_deterministic_call_loop_replay.py"
python3 "$ROOT_DIR/scripts/tests/test_replay_rebind_and_alias_holes.py"
python3 "$ROOT_DIR/scripts/tests/test_replay_scope_and_context_holes.py"

# Keep a true destruction case beside the two unknown-provenance regressions.
for diagnostic_fixture in unsupported_region_record_copy unsupported_computed_write_place rejected_region_destroyed_write; do
    set +e
    run_json_report "$ROOT_DIR/examples/$diagnostic_fixture.elisa" | python3 -c '
import json, sys
report = json.load(sys.stdin)
destroyed = sys.argv[1] == "rejected_region_destroyed_write"
assert report["status"] == "failed"
assert report["verification_state"] == ("disproved" if destroyed else "unsupported")
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
assert report["replay"]["certificates"] == report["replay"]["replayed"]
if destroyed:
    assert any(f["kind"] == "region-use-after-destroy" and f["status"] == "disproved" for f in report["findings"])
else:
    assert all(f["status"] != "disproved" for f in report["findings"])
' "$diagnostic_fixture"
    diagnostic_statuses=("${PIPESTATUS[@]}")
    set -e
    if [[ "${diagnostic_statuses[0]}" -ne 1 || "${diagnostic_statuses[1]}" -ne 0 ]]; then
        printf 'proof test matrix failed: resource diagnostic classification failed for %s\n' "$diagnostic_fixture" >&2
        exit 1
    fi
done

python3 "$ROOT_DIR/scripts/test_signed_call_snapshots.py"
