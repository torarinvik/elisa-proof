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

elisa_default_stage1() {
    local root_dir="$1"
    local compiler_root="${ELISA_COMPILER_ROOT:-${ELISA_COMPILER_SRC:-$root_dir/../Elisa-compiler}}"
    local wrapper
    if [[ -x "$compiler_root/scripts/elisac_stage1.sh" ]]; then
        wrapper="$(cd "$compiler_root" && pwd -P)/scripts/elisac_stage1.sh"
        printf '%s\n' "$wrapper"
        return 0
    fi
    # An explicit checkout must not silently select an unrelated PATH product.
    if [[ -n "${ELISA_COMPILER_ROOT:-${ELISA_COMPILER_SRC:-}}" ]]; then
        printf 'Stage1 wrapper not executable: %s/scripts/elisac_stage1.sh\n' "$compiler_root" >&2
        return 2
    fi
    command -v elisac-stage1 2>/dev/null || return 1
}

elisa_default_stage0() {
    local root_dir="$1"
    local selected="${ELISACORE_BIN:-${ELISA_STAGE0_BIN:-}}"
    local core_root
    if [[ -n "$selected" && -x "$selected" ]]; then
        printf '%s\n' "$selected"
        return 0
    fi
    core_root="${ELISA_STAGE0_CORE:-$root_dir/../../Go projects/Elisa-core}"
    if [[ -x "$core_root/compiler/bin/elisac" ]]; then
        printf '%s\n' "$(cd "$core_root" && pwd -P)/compiler/bin/elisac"
        return 0
    fi
    command -v elisac-stage0 2>/dev/null || return 1
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
