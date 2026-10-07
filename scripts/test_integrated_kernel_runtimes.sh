# shellcheck shell=bash
# Uses the primary matrix's qualified compiler and runtime setup.
for frame_probe in frame_policy_relations_runtime frame_policy_places_runtime frame_policy_certificates_runtime frame_source_places_runtime frame_source_owners_runtime frame_source_policy_runtime frame_source_writes_runtime frame_source_headers_runtime frame_source_types_runtime frame_source_admission_runtime frame_source_events_runtime frame_report_recording_runtime; do
    if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/$frame_probe.o" "$ROOT_DIR/examples/$frame_probe.elisa" >/dev/null 2>&1 ||
        ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/$frame_probe" "$standalone_probe_dir/$frame_probe.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}" ||
        ! "$standalone_probe_dir/$frame_probe"; then
        printf 'proof test matrix failed: frame policy runtime control %s failed\n' "$frame_probe" >&2
        exit 1
    fi
done
if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-quantifier-instances.o" "$ROOT_DIR/examples/kernel_quantifier_instances_runtime.elisa" >/dev/null 2>&1; then
    printf 'proof test matrix failed: direct quantifier instance probe did not compile\n' >&2
    exit 1
fi
if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-quantifier-instances" "$standalone_probe_dir/kernel-quantifier-instances.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"; then
    printf 'proof test matrix failed: direct quantifier instance probe did not link\n' >&2
    exit 1
fi
if ! "$standalone_probe_dir/kernel-quantifier-instances"; then
    printf 'proof test matrix failed: quantifier replay skipped a later instance or witness\n' >&2
    exit 1
fi
if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-interval-contradiction.o" "$ROOT_DIR/examples/kernel_interval_contradiction_runtime.elisa" >/dev/null 2>&1; then
    printf 'proof test matrix failed: direct interval contradiction probe did not compile\n' >&2
    exit 1
fi
if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-interval-contradiction" "$standalone_probe_dir/kernel-interval-contradiction.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"; then
    printf 'proof test matrix failed: direct interval contradiction probe did not link\n' >&2
    exit 1
fi
if ! "$standalone_probe_dir/kernel-interval-contradiction"; then
    printf 'proof test matrix failed: integer contradiction replay or consistent/wrap rejection failed\n' >&2
    exit 1
fi
if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-expr-equal-budget.o" "$ROOT_DIR/examples/kernel_expr_equal_budget_runtime.elisa" >/dev/null 2>&1; then
    printf 'proof test matrix failed: direct expression-equality budget probe did not compile\n' >&2
    exit 1
fi
if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-expr-equal-budget" "$standalone_probe_dir/kernel-expr-equal-budget.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"; then
    printf 'proof test matrix failed: direct expression-equality budget probe did not link\n' >&2
    exit 1
fi
if ! "$standalone_probe_dir/kernel-expr-equal-budget"; then
    printf 'proof test matrix failed: expression equality malformed-input or budget-boundary controls failed\n' >&2
    exit 1
fi
if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-contextual-constant-width.o" "$ROOT_DIR/examples/kernel_contextual_constant_width_runtime.elisa" >/dev/null 2>&1; then
    printf 'proof test matrix failed: contextual constant width/usize/budget probe did not compile\n' >&2
    exit 1
fi
if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-contextual-constant-width" "$standalone_probe_dir/kernel-contextual-constant-width.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"; then
    printf 'proof test matrix failed: contextual constant width/usize/budget probe did not link\n' >&2
    exit 1
fi
if ! "$standalone_probe_dir/kernel-contextual-constant-width"; then
    printf 'proof test matrix failed: contextual constant widths, usize refusal, or shared budget changed\n' >&2
    exit 1
fi
if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-subtraction-alias-forgery.o" "$ROOT_DIR/examples/kernel_subtraction_alias_forgery_runtime.elisa" >/dev/null 2>&1; then
    printf 'proof test matrix failed: direct subtraction alias replay probe did not compile\n' >&2
    exit 1
fi
if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-subtraction-alias-forgery" "$standalone_probe_dir/kernel-subtraction-alias-forgery.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"; then
    printf 'proof test matrix failed: direct subtraction alias replay probe did not link\n' >&2
    exit 1
fi
if ! "$standalone_probe_dir/kernel-subtraction-alias-forgery"; then
    printf 'proof test matrix failed: subtraction alias positive or forged operator/path/width/owner controls failed\n' >&2
    exit 1
fi
if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj -O0 -o "$standalone_probe_dir/kernel-tagged-comparison-admission.o" "$ROOT_DIR/examples/kernel_tagged_comparison_admission_runtime.elisa" >/dev/null 2>&1; then
    printf 'proof test matrix failed: tagged comparison admission probe did not compile\n' >&2
    exit 1
fi
if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/kernel-tagged-comparison-admission" "$standalone_probe_dir/kernel-tagged-comparison-admission.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"; then
    printf 'proof test matrix failed: tagged comparison admission probe did not link\n' >&2
    exit 1
fi
if ! "$standalone_probe_dir/kernel-tagged-comparison-admission"; then
    printf 'proof test matrix failed: tagged comparison positive, whole-arena malformed, mixed-width, or decoder-root controls failed\n' >&2
    exit 1
fi
