#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPILER="${ELISA_COMPILER_BIN:-}"
# shellcheck source=scripts/compiler_provenance.sh
source "$ROOT_DIR/scripts/compiler_provenance.sh"

if [[ -z "$COMPILER" ]]; then
    # The compilers are installed under explicit stage names; `elisac` no longer
    # exists. Prefer the self-hosted one, fall back to the Go bootstrap.
    for candidate in elisac-stage1 elisac-stage0 elisac; do
        COMPILER="$(command -v "$candidate" 2>/dev/null || true)"
        [[ -n "$COMPILER" ]] && break
    done
fi

if [[ -z "$COMPILER" || ! -x "$COMPILER" ]]; then
    printf 'Set ELISA_COMPILER_BIN to the Elisa compiler (or put elisac-stage1 / elisac-stage0 on PATH).\n' >&2
    exit 2
fi

COMPILER_IS_STAGE0=0
if elisa_compiler_is_stage0 "$COMPILER"; then
    COMPILER_IS_STAGE0=1
    # The stage0 product may be copied aside for a pinned toolchain. Identify that copy by its
    # embedded Go module path instead of allowing a renamed bootstrap binary to bypass the guard.
fi

if [[ "$COMPILER_IS_STAGE0" -eq 1 ]]; then
    elisa_verify_stage0_provenance "$COMPILER" "$ROOT_DIR" || exit $?
fi

if ! command -v clang >/dev/null 2>&1; then
    printf 'clang is required to link the generated Elisa object.\n' >&2
    exit 2
fi

# stage0 emits an object that links on its own; a stage1 object references the
# Elisa runtime (arena_alloc, the AoS store entry points, the sview helpers) and
# needs elisacore_runtime.o on the link line. Set ELISA_RUNTIME_OBJ to override;
# otherwise it is read out of the stage1 wrapper, which names its worktree.
RUNTIME_OBJ="${ELISA_RUNTIME_OBJ:-}"
COMPILER_IS_STAGE1=0
if [[ -z "$RUNTIME_OBJ" ]]; then
    driver="$(grep -o '/[^"]*/scripts/elisac_stage1\.sh' "$COMPILER" 2>/dev/null | head -1 || true)"
    if [[ -n "$driver" ]]; then
        COMPILER_IS_STAGE1=1
        candidate="${driver%/scripts/elisac_stage1.sh}/build/runtime/elisacore_runtime.o"
        [[ -f "$candidate" ]] && RUNTIME_OBJ="$candidate"
    fi
fi
if [[ "$(basename "$COMPILER")" == "elisac-stage1" ]]; then
    COMPILER_IS_STAGE1=1
fi
# The installed compiler publishes its runtime object beside itself. Used only as
# a fallback: the copy that belongs to the compiler which emitted the object is
# the one that is guaranteed to match it.
if [[ "$COMPILER_IS_STAGE1" -eq 1 && -z "$RUNTIME_OBJ" && -f "${HOME}/.elisac/elisacore_runtime.o" ]]; then
    RUNTIME_OBJ="${HOME}/.elisac/elisacore_runtime.o"
fi

mkdir -p "$ROOT_DIR/build"
cd "$ROOT_DIR"
# Compile against the pinned compiler export, never the live sibling checkout.
# shellcheck source=scripts/compiler_snapshot.sh
source "$ROOT_DIR/scripts/compiler_snapshot.sh"
if [[ "$COMPILER_IS_STAGE1" -eq 1 ]]; then
    stage1_root=""
    if [[ -n "${driver:-}" ]]; then
        stage1_root="${driver%/scripts/elisac_stage1.sh}"
    elif [[ -f "${HOME}/.elisac/stage1/SNAPSHOT" ]]; then
        stage1_root="${HOME}/.elisac/stage1"
    fi
    stage1_revision=""
    if [[ -n "$stage1_root" && -f "$stage1_root/SNAPSHOT" ]]; then
        stage1_revision="$(awk '$1 == "revision:" { print $2; exit }' "$stage1_root/SNAPSHOT")"
    fi
    if [[ -n "$stage1_revision" && "$ELISA_COMPILER_PINNED_REV" != "$stage1_revision"* ]]; then
        printf 'stage1/frontend provenance mismatch: stage1=%s frontend=%s\n' "$stage1_revision" "$ELISA_COMPILER_PINNED_REV" >&2
        exit 2
    fi
fi
PROFILE_HOOKS_SOURCE="${ELISA_PROFILE_HOOKS_SOURCE:-$SNAPSHOT_COMPILER/test/parity/profile_hooks.c}"
PROFILE_HOOKS_OBJ="${ELISA_PROFILE_HOOKS_OBJ:-$ROOT_DIR/build/profile_hooks.o}"
if [[ ! -f "$PROFILE_HOOKS_SOURCE" ]]; then
    printf 'missing profiler ABI hook source: %s\n' "$PROFILE_HOOKS_SOURCE" >&2
    exit 2
fi
if [[ ! -f "$PROFILE_HOOKS_OBJ" || "$PROFILE_HOOKS_SOURCE" -nt "$PROFILE_HOOKS_OBJ" ]]; then
    clang -c -O2 -o "$PROFILE_HOOKS_OBJ" "$PROFILE_HOOKS_SOURCE"
fi
"$COMPILER" -emit obj -O0 -o "build/elisa-proof-stage.o" "$SNAPSHOT_ROOT/src/main.elisa"
LINK_INPUTS=("build/elisa-proof-stage.o" "$PROFILE_HOOKS_OBJ")
[[ -n "$RUNTIME_OBJ" ]] && LINK_INPUTS+=("$RUNTIME_OBJ")
clang -Wl,-dead_strip -o "build/elisa-proof" "${LINK_INPUTS[@]}"
