# shellcheck shell=bash
# Part 1 of the proof test matrix; sourced in order by scripts/test.sh, never run alone.
python3 "$ROOT_DIR/scripts/check_source_length.py"
python3 "$ROOT_DIR/test/audit_harness_test.py"
"$ROOT_DIR/scripts/build.sh"
# The portable package checker is its own small product built from the same snapshot.
ELISA_PROOF_MAIN=src/replay_main.elisa ELISA_PROOF_OUTPUT="$ROOT_DIR/build/elisa-proof-replay" "$ROOT_DIR/scripts/build.sh"

# The marker-decoder regression must finish under the normal watchdog. Completion
# is not proof: unresolved obligations remain visible in the report.
if ! ELISA_FULL_AUDIT_SOURCE="$ROOT_DIR/test/repro/audit_unsigned_marker.elisa" \
    ELISA_FULL_AUDIT_BINARY="$ROOT_DIR/build/elisa-proof" \
    "$ROOT_DIR/scripts/audit_full_source.sh" | python3 -c 'import json, sys; audit=json.load(sys.stdin); assert audit["complete"]; assert audit["replay_gaps"] == 0'; then
    printf 'proof test matrix failed: unsigned-marker audit did not complete with clean replay\n' >&2
    exit 1
fi

# Buffer JSON probes so a valid-looking report cannot hide a crash or an exit/verdict mismatch.
# The downstream assertions still check the report's expected shape; this adapter checks that the
# whole JSON document parsed and that the verifier's process exit agrees with its top-level verdict.
run_json_report() {
    local source_path="$1"
    local report_path
    local proof_status
    local expected_status

    if ! report_path="$(mktemp "${TMPDIR:-/tmp}/elisa-proof-json-probe.XXXXXX")"; then
        printf 'proof test matrix failed: could not allocate a report buffer for %s\n' "$source_path" >&2
        return 98
    fi
    if "$ROOT_DIR/build/elisa-proof" --json "$source_path" >"$report_path"; then
        proof_status=0
    else
        proof_status=$?
    fi
    if ! expected_status="$(python3 - "$report_path" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
status = report.get("status")
if status == "proved":
    print(0)
elif status == "failed":
    print(1)
else:
    raise SystemExit(f"unexpected --json verdict: {status!r}")
PY
)"; then
        printf 'proof test matrix failed: verifier emitted an incomplete or malformed JSON report for %s (exit=%s)\n' "$source_path" "$proof_status" >&2
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
python3 "$ROOT_DIR/scripts/test_overlap_diagnostics.py"
python3 "$ROOT_DIR/scripts/test_certificate_reuse.py"
python3 "$ROOT_DIR/scripts/test_measurements.py"
python3 "$ROOT_DIR/scripts/test_source_admission_matrix.py"
python3 "$ROOT_DIR/scripts/test_negated_conjunction_fallthrough.py"
python3 "$ROOT_DIR/scripts/test_parameter_heavy_return_analysis.py"
python3 "$ROOT_DIR/scripts/test_numeric_cast_operator.py"
python3 "$ROOT_DIR/scripts/test_rejected_numeric_cast_operator.py"
python3 "$ROOT_DIR/scripts/test_widening_cast.py"
python3 "$ROOT_DIR/scripts/test_call_result_width.py"
python3 "$ROOT_DIR/scripts/test_adt_library.py"
python3 "$ROOT_DIR/scripts/test_adt_parser.py"
python3 "$ROOT_DIR/scripts/test_match_refuted_arms.py"
python3 "$ROOT_DIR/scripts/test_chained_pure_calls.py"
python3 "$ROOT_DIR/scripts/test_dispatcher_budget.py"
python3 "$ROOT_DIR/scripts/test_qualified_constants.py"
python3 "$ROOT_DIR/scripts/test_variant_exclusion.py"
python3 "$ROOT_DIR/scripts/test_signed_upper_bound.py"
python3 "$ROOT_DIR/scripts/test_refusal_gate.py"
python3 "$ROOT_DIR/scripts/test_report_count_semantics.py"
python3 "$ROOT_DIR/scripts/test_deterministic_call_chain.py"
python3 "$ROOT_DIR/scripts/test_deterministic_operator_global.py"
python3 "$ROOT_DIR/scripts/test_tuple_field_region.py"
python3 "$ROOT_DIR/scripts/test_enum_tag_equality.py"
python3 "$ROOT_DIR/scripts/test_signed_local_field_bounds.py"
python3 "$ROOT_DIR/scripts/test_signed_tuple_label_bounds.py"
python3 "$ROOT_DIR/scripts/test_usize_increment_under_count.py"
python3 "$ROOT_DIR/scripts/test_disequality_strictness.py"
python3 "$ROOT_DIR/scripts/test_or_chains.py"
python3 "$ROOT_DIR/scripts/test_guard_and_flag_facts.py"
python3 "$ROOT_DIR/scripts/test_min_max_abs_summaries.py"
python3 "$ROOT_DIR/scripts/test_literal_count.py"
python3 "$ROOT_DIR/scripts/test_engine_state.py"
python3 "$ROOT_DIR/scripts/test_explain.py"
python3 "$ROOT_DIR/scripts/test_long_difference_chain.py"
python3 "$ROOT_DIR/scripts/test_can_block_frame.py"
python3 "$ROOT_DIR/scripts/test_collection_push_count.py"
python3 "$ROOT_DIR/scripts/test_collection_pop.py"
python3 "$ROOT_DIR/scripts/test_census_diff.py"
python3 "$ROOT_DIR/scripts/test_refusal_census.py"
python3 "$ROOT_DIR/scripts/test_body_ensures.py"
python3 "$ROOT_DIR/scripts/test_contract_placement.py"
python3 "$ROOT_DIR/scripts/test_scalar_reference_index.py"
python3 "$ROOT_DIR/scripts/test_old_mutable_reference.py"
python3 "$ROOT_DIR/scripts/test_internal_marker_names.py"
python3 "$ROOT_DIR/scripts/test_unsigned_disjunction.py"
python3 "$ROOT_DIR/scripts/test_numeric_cast_contract.py"
python3 "$ROOT_DIR/scripts/test_source_map.py"
python3 "$ROOT_DIR/scripts/test_unsigned_distinct_constants.py"
python3 "$ROOT_DIR/scripts/test_unsigned_resource_source_policy.py"
python3 "$ROOT_DIR/scripts/test_fixed_array_constant_indices.py"
python3 "$ROOT_DIR/scripts/test_return_branch_path_fact.py"
python3 "$ROOT_DIR/scripts/test_kernel_inventory.py"
python3 "$ROOT_DIR/scripts/test_unsigned_subtraction_upper.py"
python3 "$ROOT_DIR/scripts/test_unsigned_or_goal.py"
python3 "$ROOT_DIR/scripts/test_unsigned_sum_upper_shape.py"
python3 "$ROOT_DIR/scripts/test_unsigned_remainder_range.py"
python3 "$ROOT_DIR/scripts/test_loop_state_joins.py"
python3 "$ROOT_DIR/scripts/test_portable_replay.py"
python3 "$ROOT_DIR/scripts/test_linear_certificates.py"
python3 "$ROOT_DIR/scripts/test_smt_oracle.py"
python3 "$ROOT_DIR/scripts/test_symbolic_quantifiers.py"
python3 "$ROOT_DIR/scripts/test_indexed_write_frame.py"
python3 "$ROOT_DIR/scripts/test_collection_frames.py"
python3 "$ROOT_DIR/scripts/test_loop_exit_frame.py"
python3 "$ROOT_DIR/scripts/test_near_miss.py"
python3 "$ROOT_DIR/scripts/test_pure_unfolding.py"
python3 "$ROOT_DIR/scripts/test_struct_invariants.py"
python3 "$ROOT_DIR/scripts/test_correspondence.py"
python3 "$ROOT_DIR/scripts/test_tactic_branch_regions.py"
python3 "$ROOT_DIR/scripts/test_unsigned_or_goal.py"
python3 "$ROOT_DIR/scripts/test_unsigned_sum_upper_shape.py"
python3 "$ROOT_DIR/scripts/test_vector_index_arithmetic.py"
python3 "$ROOT_DIR/scripts/test_adt_recursive_payload.py"
python3 "$ROOT_DIR/scripts/test_call_sum_premise.py"
python3 "$ROOT_DIR/scripts/test_nested_conditional_split.py"
python3 "$ROOT_DIR/scripts/test_include_constant_scope.py"
python3 "$ROOT_DIR/scripts/test_include_function_scope.py"

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
    SELF_HOST_COMPILER="$(elisa_default_stage1 "$ROOT_DIR" || true)"
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
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/report-invariants.o" "$ROOT_DIR/examples/report_invariants_runtime.elisa" >/dev/null 2>&1
report_invariants_compile_status=$?
if [[ "$report_invariants_compile_status" -ne 0 ]]; then
    printf 'proof test matrix failed: report invariant boundary harness did not compile\n' >&2
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
# This AST-level test uses the same immutable frontend export as the proof build.
# Stage0's frontend-linked object already contains the runtime definitions.
field_runtime_inputs=()
if ! elisa_compiler_is_stage0 "$SELF_HOST_COMPILER"; then
    field_runtime_inputs=("${kernel_runtime_inputs[@]}")
fi
for ast_probe in field_equality_runtime marker_dispatch_runtime; do
    if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/$ast_probe.o" "$ROOT_DIR/build/snapshot/elisa-proof/examples/$ast_probe.elisa" >/dev/null 2>&1; then
        printf 'proof test matrix failed: AST allocation optimization differential test %s did not compile\n' "$ast_probe" >&2
        exit 1
    fi
    if [[ "${#field_runtime_inputs[@]}" -gt 0 ]]; then
        if ! "${CLANG:-clang}" -Wl,-dead_strip -o "$standalone_probe_dir/$ast_probe" "$standalone_probe_dir/$ast_probe.o" "$ROOT_DIR/build/profile_hooks.o" "${field_runtime_inputs[@]}"; then
            printf 'proof test matrix failed: AST allocation differential test %s did not link\n' "$ast_probe" >&2
            exit 1
        fi
    else
        if ! "${CLANG:-clang}" -Wl,-dead_strip -o "$standalone_probe_dir/$ast_probe" "$standalone_probe_dir/$ast_probe.o" "$ROOT_DIR/build/profile_hooks.o"; then
            printf 'proof test matrix failed: AST allocation differential test %s did not link\n' "$ast_probe" >&2
            exit 1
        fi
    fi
    if ! "$standalone_probe_dir/$ast_probe"; then
        printf 'proof test matrix failed: AST allocation optimization differential test %s failed\n' "$ast_probe" >&2
        exit 1
    fi
done
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-sview-lifetimes.o" "$ROOT_DIR/examples/kernel_sview_lifetimes_runtime.elisa" >/dev/null 2>&1 &&
    "${CLANG:-clang}" -Wl,-dead_strip -o "$standalone_probe_dir/kernel-sview-lifetimes" "$standalone_probe_dir/kernel-sview-lifetimes.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}" &&
    "$standalone_probe_dir/kernel-sview-lifetimes"
if [[ "$?" -ne 0 ]]; then
    printf 'proof test matrix failed: native sview lifetime replay boundary tests failed\n' >&2
    exit 1
fi
"${CLANG:-clang}" -Wl,-dead_strip -o "$standalone_probe_dir/kernel-proposition-admission" "$standalone_probe_dir/kernel-proposition-admission.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"
"$standalone_probe_dir/kernel-proposition-admission"
kernel_proposition_admission_status=$?
if [[ "$kernel_proposition_admission_status" -ne 0 ]]; then
    printf 'proof test matrix failed: native proposition-admission boundary tests failed (%s)\n' "$kernel_proposition_admission_status" >&2
    exit 1
fi
"$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-intern.o" "$ROOT_DIR/examples/kernel_intern_runtime.elisa" >/dev/null 2>&1 &&
    "${CLANG:-clang}" -Wl,-dead_strip -o "$standalone_probe_dir/kernel-intern" "$standalone_probe_dir/kernel-intern.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}" &&
    "$standalone_probe_dir/kernel-intern"
kernel_intern_status=$?
if [[ "$kernel_intern_status" -ne 0 ]]; then
    printf 'proof test matrix failed: kernel term sharing boundary tests failed (%s)\n' "$kernel_intern_status" >&2
    exit 1
fi
"${CLANG:-clang}" -Wl,-dead_strip -o "$standalone_probe_dir/report-invariants" "$standalone_probe_dir/report-invariants.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"
"$standalone_probe_dir/report-invariants"
report_invariants_status=$?
if [[ "$report_invariants_status" -ne 0 ]]; then
    printf 'proof test matrix failed: report invariant boundary tests failed (%s)\n' "$report_invariants_status" >&2
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
# The replay checker deliberately bounds branch-state retention to keep the self-hosting corpus
# deterministic. Keep a coverage floor, require the important summaries, and require every
# budget exhaustion to be classified as unsupported rather than silently unknown.
# The peak grows with the audited kernel: 1,177,457 KB before the linear-certificate checker
# (C-02/C-03), 1,219,217 KB after it, from its 38 added obligations;
# the mocap-cleaner proof tiers raise it further, so keep the branch's 3,000,000 KB ceiling.
KERNEL_REPLAY_AUDIT_MEMORY_LIMIT_KB="${ELISA_KERNEL_REPLAY_AUDIT_MEMORY_LIMIT_KB:-3000000}"
kernel_replay_audit_dir="$standalone_probe_dir/kernel-replay-audit"
kernel_replay_audit_summary="$standalone_probe_dir/kernel-replay-audit-summary.json"
ELISA_FULL_AUDIT_SOURCE="$ROOT_DIR/examples/kernel_replay_standalone.elisa" \
    ELISA_FULL_AUDIT_BINARY="$ROOT_DIR/build/elisa-proof" \
    ELISA_FULL_AUDIT_DIR="$kernel_replay_audit_dir" \
    ELISA_FULL_AUDIT_MEMORY_LIMIT_KB="$KERNEL_REPLAY_AUDIT_MEMORY_LIMIT_KB" \
    "$ROOT_DIR/scripts/audit_full_source.sh" >"$kernel_replay_audit_summary"
kernel_replay_audit_status=$?
if [[ "$kernel_replay_audit_status" -eq 3 ]]; then
    python3 - "$kernel_replay_audit_summary" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    audit = json.load(handle)
print(
    "proof test matrix incomplete: standalone replay was stopped by the "
    f"{audit['stop_reason']} watchdog at {audit['peak_memory_kb']}/"
    f"{audit['memory_limit_kb']} KB ({audit['memory_metric']}) after "
    f"{audit['elapsed_seconds']}s; no complete proof report was emitted",
    file=sys.stderr,
)
PY
    exit 1
fi
if [[ "$kernel_replay_audit_status" -ne 0 ]]; then
    printf 'proof test matrix failed: bounded standalone audit harness failed (exit=%s)\n' \
        "$kernel_replay_audit_status" >&2
    exit 1
fi
if ! python3 "$ROOT_DIR/test/validate_kernel_replay_standalone.py" \
    <"$kernel_replay_audit_dir/proof-report.json"; then
    printf 'proof test matrix failed: standalone replay audit coverage or trust boundary regressed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["source"]["bytes"] > 0; assert report["source"]["fingerprint"]["algorithm"] == "fnv1a32"; assert 0 <= report["source"]["fingerprint"]["value"] < 2**32; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert len(report["certificates"]) == report["replay"]["certificates"]; assert report["repair_queue"] == []; assert report["trust"]["trusted_assumptions"] == []; assert report["trust"]["trusted_boundary_facts"] == len(report["trust"]["boundary_facts"]); assert all(set(fact) == {"kind", "owner", "line", "kernel_root"} for fact in report["trust"]["boundary_facts"]); assert report["replay"]["gaps"] == 0; assert all(not goal["proven"] or goal["replay_status"] == "replayed" for goal in report["goals"]); assert report["kernel"]["format"] == "elisa-proof-kernel-v1"; assert report["kernel"]["independent_replay"] is True; assert len(report["kernel"]["nodes"]) > 0; assert report["action_protocol"]["format"] == "elisa-proof-tactics-v1"; assert report["action_protocol"]["admission"] == "kernel-backed"; assert report["action_protocol"]["operations"] == ["assumption", "exact", "decide", "intro", "apply", "simp", "have", "instantiate", "rewrite", "split", "left", "right", "cases"]; assert report["action_protocol"]["branch_script"]["nested"] is True; assert report["action_protocol"]["branch_script"]["max_branch_depth"] == 32'
json_probe_status=$?
if [[ "$json_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: JSON report is not a valid structured proof state\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_quantifier.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["valid"] is True; assert report["tactic"]["solved"] is True; assert report["tactic"]["kernel_trace_replayed"] is True; assert report["tactic"]["kernel_replayed"] is True; assert report["tactic"]["certificate_replayed"] is True'
quantifier_tactic_probe_status=${PIPESTATUS[1]}
if [[ "$quantifier_tactic_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: portable quantifier tactic was not independently replayed\n' >&2
    exit 1
fi
# A range bound spelled as a wrapped literal may be an unsigned maximum, so the
# range is not known to be empty and a vacuous forall must not be admitted.
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_rejected_ambiguous_range_quantifier.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["tactic"]["valid"] is False; assert report["tactic"]["solved"] is False; assert report["tactic"]["kernel_replayed"] is False' && ambiguous_range_quantifier_status=0 || ambiguous_range_quantifier_status=${PIPESTATUS[1]}
if [[ "$ambiguous_range_quantifier_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a quantifier over an ambiguous range bound was admitted\n' >&2
    exit 1
fi
for rejected_tactic_fixture in tactic_script_rejected_large_line tactic_script_rejected_large_expr_line; do
    rejected_tactic_report="$standalone_probe_dir/$rejected_tactic_fixture.json"
    "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/$rejected_tactic_fixture.json" "$ROOT_DIR/examples/verified.elisa" >"$rejected_tactic_report"
    rejected_tactic_status=$?
    if [[ "$rejected_tactic_status" -ne 1 ]]; then
        printf 'proof test matrix failed: overflowing JSON line was accepted for %s\n' "$rejected_tactic_fixture" >&2
        exit 1
    fi
    python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert report["tactic"]["valid"] is False; assert report["tactic"]["action_count"] == 0' "$rejected_tactic_report"
    rejected_tactic_probe_status=$?
    if [[ "$rejected_tactic_probe_status" -ne 0 ]]; then
        printf 'proof test matrix failed: overflowing JSON line report was incomplete for %s\n' "$rejected_tactic_fixture" >&2
        exit 1
    fi
done
oversized_action_script="$standalone_probe_dir/tactic-script-oversized-actions.json"
python3 - "$oversized_action_script" <<'PY'
import json
import sys

script = {
    "format": "elisa-proof-tactics-v1",
    "initial": {"facts": [], "goal": {"kind": "bool", "value": True}},
    "actions": [{"action": "unknown"}] * 65537,
}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(script, handle)
PY
"$ROOT_DIR/build/elisa-proof" --tactics "$oversized_action_script" "$ROOT_DIR/examples/verified.elisa" >"$standalone_probe_dir/tactic-script-oversized-actions-report.json"
oversized_action_status=$?
if [[ "$oversized_action_status" -ne 1 ]]; then
    printf 'proof test matrix failed: oversized tactic action array was accepted\n' >&2
    exit 1
fi
python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert report["tactic"]["valid"] is False; assert report["tactic"]["action_count"] == 0' "$standalone_probe_dir/tactic-script-oversized-actions-report.json"
oversized_action_probe_status=$?
if [[ "$oversized_action_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: oversized tactic action report was incomplete\n' >&2
    exit 1
fi
for replay_fixture in replay_constant loop_accumulator arithmetic_identity equality_alias congruence summary_swapped_arguments quantifier collection_quantifier quantifier_structural_terms expression_witness call_stable_facts shared_borrow_calls writable_lend_calls region_lend_calls region_call_summary condition_call_positions product_sign frame_lifetime difference_constraints disjunctive_facts modulo_division_bounds proof_step_derivation pattern_proof pattern_or pinned_pattern pattern_scalar_literals total_match value_match value_match_nested_pure_call bounded_model loop_range_facts for_invariant for_loop_control_invariant indexed_frame slice_bounds indexn_kernel indexn_call_summary pure_index_call index_call_summary slice_call_summary fixed_array_bounds fixed_array_fields nested_call_kept_values literal_index disjunctive_goals leaving_branch_join pass_statement counting_loop_measure fixed_array_slice_bounds checked_index_fallback getelse_recovery getelse_checked_index getelse_call getelse_loop_control getelse_raise catch_expression catch_nested_pure_arm_call loop_control_invariant continue_decreases continue_decreases_branch shorthand_member constructor_kernel dogfood_kernel region_allocation region_statement region_auto_close region_new_call_argument region_new_mutable_call_argument unsigned_alias resource_nested_scalar_call body_ensures contract_placement replay_qualified_constant_argument; do
    run_json_report "$ROOT_DIR/examples/$replay_fixture.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0'
    replay_probe_status=$?
    if [[ "$replay_probe_status" -ne 0 ]]; then
        printf 'proof test matrix failed: replay coverage for %s\n' "$replay_fixture" >&2
        exit 1
    fi
done
run_json_report "$ROOT_DIR/examples/region_allocation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-open" in kinds and "resource-region-alloc" in kinds and "resource-region-bind" in kinds and "resource-region-alloc-discard" in kinds and "resource-region-close" in kinds'
region_allocation_probe_status=${PIPESTATUS[1]}
if [[ "$region_allocation_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: new[r] allocation/binding/discard transitions were not replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_generic_allocation.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-param" in kinds and "resource-region-return-alloc" in kinds and "resource-region-return" in kinds and "resource-call-region" in kinds and "resource-call-result" in kinds'
region_generic_probe_status=${PIPESTATUS[1]}
if [[ "$region_generic_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic new[r] call/result was not replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_new_call_argument.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert "resource-region-call-alloc" in kinds and any(node["kind"] == "resource-call-arg" and node["operator"] == "region-new" for node in report["kernel"]["nodes"])'
region_new_call_probe_status=${PIPESTATUS[1]}
if [[ "$region_new_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: direct new[r] call temporary was not independently replayed\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_new_mutable_call_argument.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-region-call-alloc" for node in report["kernel"]["nodes"])'
region_new_mutable_call_probe_status=${PIPESTATUS[1]}
if [[ "$region_new_mutable_call_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: mutable new[r] call temporary was not independently replayed\n' >&2
    exit 1
fi
set +e
rejected_region_new_return_report="$standalone_probe_dir/rejected-region-new-return.json"
run_json_report "$ROOT_DIR/examples/rejected_region_new_return_argument.elisa" >"$rejected_region_new_return_report"
rejected_region_new_return_status=$?
set -e
if [[ "$rejected_region_new_return_status" -ne 1 ]]; then
    printf 'proof test matrix failed: new[r] temporary escaped through a reference return\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "borrow-escape" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_region_new_return_report"; then
    printf 'proof test matrix failed: region temporary escape report was incomplete\n' >&2
    exit 1
fi
set +e
rejected_reference_return_alias_report="$standalone_probe_dir/rejected-reference-return-alias.json"
run_json_report "$ROOT_DIR/examples/rejected_reference_return_alias.elisa" >"$rejected_reference_return_alias_report"
rejected_reference_return_alias_status=$?
set -e
if [[ "$rejected_reference_return_alias_status" -ne 1 ]]; then
    printf 'proof test matrix failed: reference-return alias was accepted as an independent capability\n' >&2
    exit 1
fi
if ! python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert any(f["kind"] == "resource-use-after-move" for f in report["findings"]); assert report["replay"]["gaps"] == 0' "$rejected_reference_return_alias_report"; then
    printf 'proof test matrix failed: reference-return alias report was incomplete\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/region_statement.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = [node["kind"] for node in report["kernel"]["nodes"]]; assert kinds.count("resource-region-open") == 1 and kinds.count("resource-region-close") == 1 and "resource-region-alloc" in kinds and "resource-region-bind" in kinds and "resource-region-alloc-discard" in kinds'
region_statement_probe_status=${PIPESTATUS[1]}
if [[ "$region_statement_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: canonical region statement transitions were not replayed\n' >&2
    exit 1
fi
