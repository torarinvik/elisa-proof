# R-004 report/declaration inventory completeness and non-proved partial outcomes.
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/report-invariants" \
    "$standalone_probe_dir/report-invariants.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/focused-source-binding" \
    "$standalone_probe_dir/focused-source-binding.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/assert-by-branch-invariants" \
    "$standalone_probe_dir/assert-by-branch-invariants.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$standalone_probe_dir/assert-by-loop-invariants" \
    "$standalone_probe_dir/assert-by-loop-invariants.o" "$ROOT_DIR/build/profile_hooks.o" "${kernel_runtime_inputs[@]}"
ELISA_PROOF_BIN="$ROOT_DIR/build/elisa-proof" \
ELISA_REPORT_INVENTORY_HARNESS="$standalone_probe_dir/report-invariants" \
ELISA_FOCUSED_SOURCE_BINDING_HARNESS="$standalone_probe_dir/focused-source-binding" \
ELISA_ASSERT_BY_BRANCH_HARNESS="$standalone_probe_dir/assert-by-branch-invariants" \
ELISA_ASSERT_BY_LOOP_HARNESS="$standalone_probe_dir/assert-by-loop-invariants" \
    python3 "$ROOT_DIR/scripts/tests/test_report_inventory_completeness.py"
ELISA_PROOF_BIN="$ROOT_DIR/build/elisa-proof" \
ELISA_FOCUSED_SOURCE_BINDING_HARNESS="$standalone_probe_dir/focused-source-binding" \
    python3 "$ROOT_DIR/scripts/tests/test_focused_source_binding.py"
