python3 "$ROOT_DIR/scripts/test_checked_in_stage0_revision.py"
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
