# Build the target-native POSIX reader from the same immutable snapshot as the Elisa objects.
PORTABLE_FILE_STAMP="$PORTABLE_FILE_OBJ.clang"
PORTABLE_FILE_SNAPSHOT_SOURCE="$SNAPSHOT_ROOT/src/app/portable_file_posix.c"
if [[ -f "$ROOT_DIR/src/app/portable_file_posix.c" && ! -f "$PORTABLE_FILE_SNAPSHOT_SOURCE" ]]; then
    printf 'build: native portable-file helper is missing from the immutable source snapshot\n' >&2
    exit 2
fi
if [[ -f "$PORTABLE_FILE_SNAPSHOT_SOURCE" && ! -f "$ROOT_DIR/src/app/portable_file_posix.c" ]]; then
    printf 'build: immutable snapshot contains an unknown native portable-file helper\n' >&2
    exit 2
fi
if [[ -f "$PORTABLE_FILE_SNAPSHOT_SOURCE" ]] && ! cmp -s "$ROOT_DIR/src/app/portable_file_posix.c" "$PORTABLE_FILE_SNAPSHOT_SOURCE"; then
    printf 'build: native portable-file helper differs from the immutable source snapshot\n' >&2
    exit 2
fi
if [[ -f "$PORTABLE_FILE_SNAPSHOT_SOURCE" ]]; then
    portable_file_source="$PORTABLE_FILE_SNAPSHOT_SOURCE"
    portable_file_recipe="$(elisa_sha256 "$CLANG_TOOL" | cut -d' ' -f1) $(elisa_sha256 "$portable_file_source" | cut -d' ' -f1) -std=c11 -O2"
    portable_file_stamp="$portable_file_recipe"
    if [[ -f "$PORTABLE_FILE_OBJ" ]]; then
        portable_file_stamp+=" $(elisa_sha256 "$PORTABLE_FILE_OBJ" | cut -d' ' -f1)"
    fi
    if [[ ! -f "$PORTABLE_FILE_OBJ" || ! -f "$PORTABLE_FILE_STAMP" || "$(<"$PORTABLE_FILE_STAMP")" != "$portable_file_stamp" ]]; then
        "$CLANG_TOOL" -std=c11 -c -O2 -o "$PORTABLE_FILE_TEMP" "$portable_file_source"
        mv -f "$PORTABLE_FILE_TEMP" "$PORTABLE_FILE_OBJ"
        printf '%s %s\n' "$portable_file_recipe" "$(elisa_sha256 "$PORTABLE_FILE_OBJ" | cut -d' ' -f1)" > "$PORTABLE_FILE_STAMP"
    fi
fi
