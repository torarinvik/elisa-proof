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
run_py_test test_record_fixed_arrays.py
run_py_test test_qualified_block_ranges.py
run_py_test test_float_integer_bounds.py
run_py_test test_scalar_field_priority.py
run_py_test test_float_scalar_resources.py
run_py_test test_indexed_scalar_snapshot.py
run_py_test test_captured_loop_entry.py
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
run_py_test test_loop_state_joins.py
run_py_test test_captured_loop_constants.py
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

set +e
# Shared compiler identity checks and freshness-aware default selection.
# shellcheck source=scripts/compiler_provenance.sh
source "$ROOT_DIR/scripts/compiler_provenance.sh"
SELF_HOST_COMPILER="${ELISA_COMPILER_BIN:-}"
if [[ -z "$SELF_HOST_COMPILER" ]]; then
    # The standalone probes should use the same freshest compiler selection as
    # build.sh, with the checked-out stage1 wrapper preferred over PATH snapshots.
    compiler_selection_status=0
    SELF_HOST_COMPILER="$(elisa_default_stage1 "$ROOT_DIR")" || compiler_selection_status=$?
    [[ "$compiler_selection_status" -ne 2 ]] || exit 2
    if [[ -z "$SELF_HOST_COMPILER" ]]; then
        SELF_HOST_COMPILER="$(elisa_default_stage0 "$ROOT_DIR" || true)"
    fi
    if [[ -z "$SELF_HOST_COMPILER" ]]; then
        SELF_HOST_COMPILER="$(command -v elisac 2>/dev/null || true)"
    fi
fi
# The standalone probes below invoke the selected compiler directly, so repeat the
# same stage0 identity check that protects the main proof build.
if elisa_compiler_is_stage0 "$SELF_HOST_COMPILER"; then
    elisa_verify_stage0_provenance "$SELF_HOST_COMPILER" "$ROOT_DIR" || exit $?
fi
# Proof fixtures intentionally include unproven and refuted contracts. Import them
# in permissive compiler mode so the proof assistant, rather than the compiler's
# strict contract gate, reports the verification result.
PROOF_IMPORT_FLAGS=(-permissive)
standalone_probe_dir="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-test.XXXXXX")"
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-replay-standalone.o" "$ROOT_DIR/examples/kernel_replay_standalone.elisa" >/dev/null 2>&1
kernel_replay_standalone_status=$?
if [[ "$kernel_replay_standalone_status" -ne 0 ]]; then
    printf 'proof test matrix failed: source-neutral replay module is not standalone-compilable\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-proposition-admission.o" "$ROOT_DIR/examples/kernel_proposition_admission_runtime.elisa" >/dev/null 2>&1
kernel_proposition_admission_compile_status=$?
if [[ "$kernel_proposition_admission_compile_status" -ne 0 ]]; then
    printf 'proof test matrix failed: native proposition-admission harness did not compile\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/report-branch-accounting.o" "$ROOT_DIR/examples/report_branch_accounting_runtime.elisa"
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/report-invariants.o" "$ROOT_DIR/examples/report_invariants_runtime.elisa" >/dev/null 2>&1
report_invariants_compile_status=$?
if [[ "$report_invariants_compile_status" -ne 0 ]]; then
    printf 'proof test matrix failed: report invariant boundary harness did not compile\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/assert-by-branch-invariants.o" "$ROOT_DIR/examples/source_assert_by_branch_inventory_runtime.elisa" >/dev/null 2>&1
assert_by_branch_compile_status=$?
if [[ "$assert_by_branch_compile_status" -ne 0 ]]; then
    printf 'proof test matrix failed: assert-by branch identity harness did not compile\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/assert-by-loop-invariants.o" "$ROOT_DIR/examples/source_assert_by_loop_inventory_runtime.elisa" >/dev/null 2>&1
assert_by_loop_compile_status=$?
if [[ "$assert_by_loop_compile_status" -ne 0 ]]; then
    printf 'proof test matrix failed: assert-by loop identity harness did not compile\n' >&2
    exit 1
fi
ELISA_COMPILER_BIN="$SELF_HOST_COMPILER" python3 "$ROOT_DIR/scripts/test_loop_invariants_compile.py" || exit 1
kernel_runtime_inputs=()
kernel_runtime_obj="${ELISA_RUNTIME_OBJ:-}"
if [[ -z "$kernel_runtime_obj" ]]; then
    kernel_driver="$(grep -o '/[^\"]*/scripts/elisac_stage1\.sh' "$SELF_HOST_COMPILER" 2>/dev/null | head -1 || true)"
    if [[ -z "$kernel_driver" && "$(basename "$SELF_HOST_COMPILER")" == "elisac_stage1.sh" ]]; then
        kernel_driver="$SELF_HOST_COMPILER"
    fi
    if [[ -n "$kernel_driver" ]]; then
        kernel_runtime_candidate="${kernel_driver%/scripts/elisac_stage1.sh}/build/runtime/elisacore_runtime.o"
        [[ -f "$kernel_runtime_candidate" ]] && kernel_runtime_obj="$kernel_runtime_candidate"
    fi
fi
if [[ -z "$kernel_runtime_obj" && "$(basename "$SELF_HOST_COMPILER")" == "elisac-stage1" && -f "${HOME}/.elisac/elisacore_runtime.o" ]]; then
    kernel_runtime_obj="${HOME}/.elisac/elisacore_runtime.o"
fi
if [[ -z "$kernel_runtime_obj" ]] && elisa_compiler_is_stage0 "$SELF_HOST_COMPILER"; then
    pinned_runtime_source="$ROOT_DIR/build/snapshot/Elisa-compiler/elisacore_std/native_runtime_support.elisa"
    if [[ ! -f "$pinned_runtime_source" ]]; then
        printf 'proof test matrix failed: pinned native runtime source is missing\n' >&2
        exit 1
    fi
    kernel_runtime_obj="$standalone_probe_dir/elisacore_runtime.o"
    "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$kernel_runtime_obj" "$pinned_runtime_source" >/dev/null 2>&1
    pinned_runtime_compile_status=$?
    if [[ "$pinned_runtime_compile_status" -ne 0 ]]; then
        printf 'proof test matrix failed: pinned native runtime did not compile under stage0\n' >&2
        exit 1
    fi
fi
[[ -n "$kernel_runtime_obj" ]] && kernel_runtime_inputs+=("$kernel_runtime_obj")
source "$ROOT_DIR/scripts/test_integrated_kernel_runtimes.sh"
# This AST-level test uses the same immutable frontend export as the proof build.
# Stage0's frontend-linked object already contains the runtime definitions.
field_runtime_inputs=()
if ! elisa_compiler_is_stage0 "$SELF_HOST_COMPILER"; then
    field_runtime_inputs=("${kernel_runtime_inputs[@]}")
fi
source "$ROOT_DIR/scripts/test_source_snapshot_runtimes.sh"
for ast_probe in field_equality_runtime marker_dispatch_runtime; do
    if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/$ast_probe.o" "$ROOT_DIR/build/snapshot/elisa-proof/examples/$ast_probe.elisa" >/dev/null 2>&1; then
        printf 'proof test matrix failed: AST allocation optimization differential test %s did not compile\n' "$ast_probe" >&2
        exit 1
    fi
    if [[ "${#field_runtime_inputs[@]}" -gt 0 ]]; then
        if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/$ast_probe" "$standalone_probe_dir/$ast_probe.o" "$ROOT_DIR/build/profile_hooks.o" "${field_runtime_inputs[@]}"; then
            printf 'proof test matrix failed: AST allocation differential test %s did not link\n' "$ast_probe" >&2
            exit 1
        fi
    else
        if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/$ast_probe" "$standalone_probe_dir/$ast_probe.o" "$ROOT_DIR/build/profile_hooks.o"; then
            printf 'proof test matrix failed: AST allocation differential test %s did not link\n' "$ast_probe" >&2
            exit 1
        fi
    fi
    if ! "$standalone_probe_dir/$ast_probe"; then
        printf 'proof test matrix failed: AST allocation optimization differential test %s failed\n' "$ast_probe" >&2
        exit 1
    fi
done
if ! elisa_compiler_is_stage0 "$SELF_HOST_COMPILER"; then
    if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O2 -o "$standalone_probe_dir/conditional-signed-unit-shift-runtime.o" "$ROOT_DIR/examples/conditional_signed_unit_shift_runtime.elisa" >/dev/null 2>&1 ||
        ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/conditional-signed-unit-shift-runtime" "$standalone_probe_dir/conditional-signed-unit-shift-runtime.o" "$ROOT_DIR/build/profile_hooks.o" "${field_runtime_inputs[@]}" ||
        ! "$standalone_probe_dir/conditional-signed-unit-shift-runtime"; then
        printf 'proof test matrix failed: Stage1 signed unit-shift runtime boundary control\n' >&2
        exit 1
    fi
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-sview-lifetimes.o" "$ROOT_DIR/examples/kernel_sview_lifetimes_runtime.elisa" >/dev/null 2>&1 &&
    "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-sview-lifetimes" "$standalone_probe_dir/kernel-sview-lifetimes.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}" &&
    "$standalone_probe_dir/kernel-sview-lifetimes"
if [[ "$?" -ne 0 ]]; then
    printf 'proof test matrix failed: native sview lifetime replay boundary tests failed\n' >&2
    exit 1
fi
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-proposition-admission" "$standalone_probe_dir/kernel-proposition-admission.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"
"$standalone_probe_dir/kernel-proposition-admission"
kernel_proposition_admission_status=$?
if [[ "$kernel_proposition_admission_status" -ne 0 ]]; then
    printf 'proof test matrix failed: native proposition-admission boundary tests failed (%s)\n' "$kernel_proposition_admission_status" >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-intern.o" "$ROOT_DIR/examples/kernel_intern_runtime.elisa" >/dev/null 2>&1 &&
    "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-intern" "$standalone_probe_dir/kernel-intern.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}" &&
    "$standalone_probe_dir/kernel-intern"
kernel_intern_status=$?
if [[ "$kernel_intern_status" -ne 0 ]]; then
    printf 'proof test matrix failed: kernel term sharing boundary tests failed (%s)\n' "$kernel_intern_status" >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/region-allocation.o" "$ROOT_DIR/examples/region_allocation.elisa" >/dev/null 2>&1
region_allocation_compiler_status=$?
if [[ "$region_allocation_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected valid new[r] allocation\n' >&2
    exit 1
fi
if [[ "$(basename "$SELF_HOST_COMPILER")" == "elisac-stage1" ]]; then
    "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/region-generic-allocation.o" "$ROOT_DIR/examples/region_generic_allocation.elisa" >/dev/null 2>&1
    region_generic_compiler_status=$?
    if [[ "$region_generic_compiler_status" -ne 0 ]]; then
        printf 'proof test matrix failed: stage1 rejected region-polymorphic new[r] allocation\n' >&2
        exit 1
    fi
    "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/region-new-call.o" "$ROOT_DIR/examples/region_new_call_argument.elisa" >/dev/null 2>&1
    region_new_call_compiler_status=$?
    if [[ "$region_new_call_compiler_status" -ne 0 ]]; then
        printf 'proof test matrix failed: stage1 rejected new[r] passed to a reference formal\n' >&2
        exit 1
    fi
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/region-statement.o" "$ROOT_DIR/examples/region_statement.elisa" >/dev/null 2>&1
region_statement_compiler_status=$?
if [[ "$region_statement_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected canonical region statement form\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-duplicate-alias.o" "$ROOT_DIR/examples/rejected_region_duplicate_mutable_alias.elisa" >/dev/null 2>&1
rejected_region_duplicate_alias_compiler_status=$?
if [[ "$rejected_region_duplicate_alias_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid duplicate-alias proof fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-assign-duplicate-owner.o" "$ROOT_DIR/examples/rejected_region_assign_duplicate_owner.elisa" >/dev/null 2>&1
rejected_region_assign_duplicate_owner_compiler_status=$?
if [[ "$rejected_region_assign_duplicate_owner_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid duplicate-owner assignment fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-bind-mutable-external.o" "$ROOT_DIR/examples/rejected_region_bind_mutable_external.elisa" >/dev/null 2>&1
rejected_region_bind_mutable_external_compiler_status=$?
if [[ "$rejected_region_bind_mutable_external_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid mutable region-bind fixture\n' >&2
    exit 1
fi
if [[ "$(basename "$SELF_HOST_COMPILER")" == "elisac-stage1" ]]; then
    "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-region-call-result-duplicate-owner.o" "$ROOT_DIR/examples/rejected_region_call_result_duplicate_owner.elisa" >/dev/null 2>&1
    rejected_region_call_result_duplicate_owner_compiler_status=$?
    if [[ "$rejected_region_call_result_duplicate_owner_compiler_status" -ne 0 ]]; then
        printf 'proof test matrix failed: stage1 rejected the runtime-valid duplicate-owner call-result fixture\n' >&2
        exit 1
    fi
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-borrow-after-move.o" "$ROOT_DIR/examples/rejected_borrow_after_move.elisa" >/dev/null 2>&1
rejected_borrow_after_move_compiler_status=$?
if [[ "$rejected_borrow_after_move_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid borrow-after-move fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-negative-affine-difference.o" "$ROOT_DIR/examples/rejected_negative_affine_difference.elisa" >/dev/null 2>&1
rejected_negative_affine_difference_compiler_status=$?
if [[ "$rejected_negative_affine_difference_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the signed-affine regression fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-negative-affine-goal.o" "$ROOT_DIR/examples/rejected_negative_affine_goal.elisa" >/dev/null 2>&1
rejected_negative_affine_goal_compiler_status=$?
if [[ "$rejected_negative_affine_goal_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the signed-affine goal regression fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-overloaded-primitive-rewrite.o" "$ROOT_DIR/examples/rejected_overloaded_primitive_rewrite.elisa" >/dev/null 2>&1
rejected_overloaded_primitive_rewrite_compiler_status=$?
if [[ "$rejected_overloaded_primitive_rewrite_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the valid primitive-overload audit fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-overloaded-primitive-global-rewrite.o" "$ROOT_DIR/examples/rejected_overloaded_primitive_global_rewrite.elisa" >/dev/null 2>&1
rejected_overloaded_primitive_global_rewrite_compiler_status=$?
if [[ "$rejected_overloaded_primitive_global_rewrite_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the valid global primitive-overload audit fixture\n' >&2
    exit 1
fi
for overloaded_literal_fixture in rejected_overloaded_literal_equality rejected_overloaded_literal_fact rejected_overloaded_literal_rewrite; do
    "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/$overloaded_literal_fixture.o" "$ROOT_DIR/examples/$overloaded_literal_fixture.elisa" >/dev/null 2>&1
    overloaded_literal_compiler_status=$?
    if [[ "$overloaded_literal_compiler_status" -ne 0 ]]; then
        printf 'proof test matrix failed: compiler rejected the valid literal-overload audit fixture %s\n' "$overloaded_literal_fixture" >&2
        exit 1
    fi
done
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-overloaded-runtime-assert.o" "$ROOT_DIR/examples/rejected_overloaded_runtime_assert.elisa" >/dev/null 2>&1
rejected_overloaded_runtime_assert_compiler_status=$?
if [[ "$rejected_overloaded_runtime_assert_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the valid runtime-assert overload audit fixture\n' >&2
    exit 1
fi
rejected_borrow_call_duplicate_alias_report="$standalone_probe_dir/rejected-borrow-call-duplicate-alias.log"
if "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-borrow-call-duplicate-alias.o" "$ROOT_DIR/examples/rejected_borrow_call_duplicate_alias.elisa" >"$rejected_borrow_call_duplicate_alias_report" 2>&1; then
    printf 'proof test matrix failed: compiler accepted overlapping mutable call arguments\n' >&2
    exit 1
fi
if ! grep -Fq 'call "write_pair" passes "x" to mutable reference parameter "right" while argument for "left" refers to overlapping memory' "$rejected_borrow_call_duplicate_alias_report"; then
    printf 'proof test matrix failed: duplicate mutable call aliases lacked the expected overlap diagnostic\n' >&2
    cat "$rejected_borrow_call_duplicate_alias_report" >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/rejected-unsigned-overflow-goal.o" "$ROOT_DIR/examples/rejected_unsigned_overflow_goal.elisa" >/dev/null 2>&1
rejected_unsigned_overflow_goal_compiler_status=$?
if [[ "$rejected_unsigned_overflow_goal_compiler_status" -ne 0 ]]; then
    printf 'proof test matrix failed: compiler rejected the runtime-valid unsigned overflow fixture\n' >&2
    exit 1
fi
"$SELF_HOST_COMPILER" -emit obj -O0 -o "$standalone_probe_dir/nested-region-destroy.o" "$ROOT_DIR/examples/rejected_region_destroy_nested_without_binding.elisa" >/dev/null 2>&1
nested_region_destroy_compiler_status=$?
if [[ "$nested_region_destroy_compiler_status" -eq 0 ]]; then
    printf 'proof test matrix failed: compiler accepted nested destruction/reopening of an inherited region\n' >&2
    exit 1
fi
