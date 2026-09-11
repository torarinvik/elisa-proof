#!/usr/bin/env bash

# Shared compiler identity checks for every path that invokes a compiler directly.
# A build guard alone is insufficient when test or dogfood probes compile fixtures
# outside the main proof build.

elisa_compiler_is_stage0() {
    local compiler="$1"
    [[ "$(basename "$compiler")" == "elisac-stage0" ]] && return 0
    go version -m "$compiler" 2>/dev/null \
        | awk '$1 == "path" && $2 == "elisacore/src" { found = 1 } END { exit !found }'
}

elisa_verify_stage0_provenance() {
    local compiler="$1"
    local root_dir="${2:-.}"
    local expected_file="${ELISA_STAGE0_REV_FILE:-$root_dir/ELISA_STAGE0_REV}"
    local build_info
    local revision
    local modified
    local expected

    build_info="$(go version -m "$compiler" 2>/dev/null || true)"
    revision="$(printf '%s\n' "$build_info" | awk '$1 == "build" && $2 ~ /^vcs.revision=/ { sub(/^vcs.revision=/, "", $2); print $2; exit }')"
    modified="$(printf '%s\n' "$build_info" | awk '$1 == "build" && $2 ~ /^vcs.modified=/ { sub(/^vcs.modified=/, "", $2); print $2; exit }')"
    if [[ ! -f "$expected_file" ]]; then
        printf 'stage0 provenance unavailable: %s is missing\n' "$expected_file" >&2
        return 2
    fi
    expected="$(tr -d '[:space:]' < "$expected_file")"
    if [[ -z "$revision" || -z "$expected" ]]; then
        printf 'stage0 provenance unavailable: compiler has no embedded VCS revision\n' >&2
        return 2
    fi
    if [[ "$revision" != "$expected"* ]]; then
        printf 'stage0 provenance mismatch: binary=%s expected=%s\n' "$revision" "$expected" >&2
        return 2
    fi
    if [[ "$modified" != "false" ]]; then
        printf 'stage0 provenance mismatch: compiler was built from modified sources\n' >&2
        return 2
    fi
    return 0
}
