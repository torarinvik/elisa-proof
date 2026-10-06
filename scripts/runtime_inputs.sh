#!/usr/bin/env bash

# Resolve the runtime used to link stage1 output. Keep this as a small shell helper so
# build-time selection can be tested with mocked compiler paths without invoking a compiler.
elisa_resolve_runtime_obj() {
    local compiler="$1"
    local compiler_is_stage0="$2"
    local driver=""
    local compiler_root="${ELISA_COMPILER_ROOT:-${ELISA_COMPILER_SRC:-}}"
    local candidate=""

    RUNTIME_OBJ=""
    COMPILER_IS_STAGE1=0
    ELISA_RESOLVED_STAGE1_ROOT=""
    if [[ "$compiler_is_stage0" -ne 1 ]]; then
        driver="$(grep -o '/[^\"]*/scripts/elisac_stage1\.sh' "$compiler" 2>/dev/null | head -1 || true)"
        if [[ -z "$driver" && "$(basename "$compiler")" == "elisac_stage1.sh" ]]; then
            driver="$compiler"
        fi
        if [[ -n "$driver" || "$(basename "$compiler")" == "elisac-stage1" ]]; then
            COMPILER_IS_STAGE1=1
        fi
        if [[ -n "$driver" ]]; then
            ELISA_RESOLVED_STAGE1_ROOT="${driver%/scripts/elisac_stage1.sh}"
        elif [[ "$COMPILER_IS_STAGE1" -eq 1 && -n "$compiler_root" ]]; then
            ELISA_RESOLVED_STAGE1_ROOT="$compiler_root"
        fi
    fi

    if [[ -n "${ELISA_RUNTIME_OBJ:-}" ]]; then
        if [[ ! -f "$ELISA_RUNTIME_OBJ" ]]; then
            printf 'Elisa runtime object not found: %s\n' "$ELISA_RUNTIME_OBJ" >&2
            return 2
        fi
        RUNTIME_OBJ="$ELISA_RUNTIME_OBJ"
        return 0
    fi

    # Stage0 output has no runtime dependency. Do not accidentally add the installed
    # Stage1 runtime just because one happens to be present in HOME.
    [[ "$compiler_is_stage0" -eq 1 ]] && return 0

    if [[ -n "$driver" ]]; then
        candidate="${driver%/scripts/elisac_stage1.sh}/build/runtime/elisacore_runtime.o"
        if [[ -f "$candidate" ]]; then
            RUNTIME_OBJ="$candidate"
            return 0
        fi
        printf 'Stage1 wrapper runtime object not found: %s\n' "$candidate" >&2
        return 2
    fi

    if [[ "$(basename "$compiler")" == "elisac-stage1" ]]; then
        if [[ -n "$compiler_root" ]]; then
            candidate="$compiler_root/build/runtime/elisacore_runtime.o"
            if [[ -f "$candidate" ]]; then
                RUNTIME_OBJ="$candidate"
                return 0
            fi
            printf 'Stage1 source runtime object not found: %s\n' "$candidate" >&2
            return 2
        fi
        # Preserve installed Stage1 behavior only when no matching source checkout is known.
        candidate="${HOME:-}/.elisac/elisacore_runtime.o"
        if [[ -f "$candidate" ]]; then
            RUNTIME_OBJ="$candidate"
            return 0
        fi
        printf 'Stage1 requires its matching runtime object; set ELISA_RUNTIME_OBJ\n' >&2
        return 2
    fi
    return 0
}
