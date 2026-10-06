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
        elif [[ "$COMPILER_IS_STAGE1" -eq 1 && "$(basename "$compiler")" == "elisac-stage1" ]]; then
            # An explicitly selected Stage1 executable carries enough location
            # context to find its source checkout. Only accept this inference when
            # that checkout has the provenance metadata used by stage1 builds.
            local inferred_root
            inferred_root="$(cd "$(dirname "$compiler")/.." 2>/dev/null && pwd -P || true)"
            if [[ -n "$inferred_root" \
                  && -f "$inferred_root/scripts/stage1_provenance.py" \
                  && -f "$inferred_root/bin/elisac-stage1.provenance.json" \
                  && -f "$inferred_root/build/runtime/elisacore_runtime.o" ]]; then
                ELISA_RESOLVED_STAGE1_ROOT="$inferred_root"
            fi
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
        if [[ -n "$ELISA_RESOLVED_STAGE1_ROOT" ]]; then
            candidate="$ELISA_RESOLVED_STAGE1_ROOT/build/runtime/elisacore_runtime.o"
            if [[ -f "$candidate" ]]; then
                RUNTIME_OBJ="$candidate"
                return 0
            fi
            printf 'Stage1 selected-source runtime object not found: %s\n' "$candidate" >&2
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
