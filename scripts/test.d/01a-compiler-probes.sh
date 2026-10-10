# shellcheck shell=bash
# Ordered compiler probes; shares state with the preceding setup part.
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
