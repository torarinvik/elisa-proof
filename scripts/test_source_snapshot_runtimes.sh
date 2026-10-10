# Sourced after the parent matrix resolves its compiler, runtime and link flags.
# Exercise source predicates at both optimizer settings as well as CLI reports.
for source_snapshot_probe in indexed_snapshot_source_runtime captured_loop_entry_source_runtime; do
    for source_snapshot_level in O0 O2; do
        source_snapshot_product="$standalone_probe_dir/$source_snapshot_probe-$source_snapshot_level"
        if ! "$SELF_HOST_COMPILER" "${PROOF_IMPORT_FLAGS[@]}" -emit obj "-$source_snapshot_level" -o "$source_snapshot_product.o" "$ROOT_DIR/examples/$source_snapshot_probe.elisa"; then
            printf 'proof test matrix failed: source snapshot probe %s %s did not compile\n' "$source_snapshot_probe" "$source_snapshot_level" >&2
            exit 1
        fi
        if ! "${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$source_snapshot_product" "$source_snapshot_product.o" "$ROOT_DIR/build/profile_hooks.o" "${field_runtime_inputs[@]}"; then
            printf 'proof test matrix failed: source snapshot probe %s %s did not link\n' "$source_snapshot_probe" "$source_snapshot_level" >&2
            exit 1
        fi
        if ! "$source_snapshot_product"; then
            printf 'proof test matrix failed: source snapshot probe %s %s failed\n' "$source_snapshot_probe" "$source_snapshot_level" >&2
            exit 1
        fi
    done
done
