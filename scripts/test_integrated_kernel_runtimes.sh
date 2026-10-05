# shellcheck shell=bash
# Uses the primary matrix's qualified compiler and runtime setup.
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
