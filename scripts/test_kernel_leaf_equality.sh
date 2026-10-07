#!/usr/bin/env bash
# Focused strict native regression for the kernel's expression-equality boundary.
set -euo pipefail

LEAF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LEAF_ROOT/scripts/compiler_provenance.sh"
source "$LEAF_ROOT/scripts/link_flags.sh"
LEAF_COMPILER="$(elisa_default_stage0 "$LEAF_ROOT")" || { printf 'pinned stage0 compiler not found\n' >&2; exit 2; }
if ! elisa_compiler_is_stage0 "$LEAF_COMPILER"; then
    printf 'this focused regression requires the pinned stage0 compiler\n' >&2
    exit 2
fi
elisa_verify_stage0_provenance "$LEAF_COMPILER" "$LEAF_ROOT"
LEAF_RUNTIME_SOURCE="$LEAF_ROOT/build/snapshot/Elisa-compiler/elisacore_std/native_runtime_support.elisa"
LEAF_REV="$(tr -d '[:space:]' < "$LEAF_ROOT/ELISA_COMPILER_REV")"
if [[ -z "$LEAF_REV" || ! -f "$LEAF_RUNTIME_SOURCE" || ! -f "$LEAF_ROOT/build/snapshot/Elisa-compiler/.rev" ]] ||
   [[ "$(<"$LEAF_ROOT/build/snapshot/Elisa-compiler/.rev")" != "$LEAF_REV"* ]]; then
    printf 'build the pinned proof snapshot before running this regression\n' >&2
    exit 2
fi
LEAF_SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/elisa-kernel-leaf.XXXXXX")"
cleanup_leaf() {
    rm -f -- "$LEAF_SCRATCH/runtime.o" "$LEAF_SCRATCH/probe.o" "$LEAF_SCRATCH/probe" "$LEAF_SCRATCH/congruence.o" "$LEAF_SCRATCH/congruence"
    rmdir -- "$LEAF_SCRATCH"
}
trap cleanup_leaf EXIT
"$LEAF_COMPILER" -emit obj -O0 -o "$LEAF_SCRATCH/runtime.o" "$LEAF_RUNTIME_SOURCE"
"$LEAF_COMPILER" -emit obj -O0 -o "$LEAF_SCRATCH/probe.o" "$LEAF_ROOT/examples/kernel_interval_contradiction_runtime.elisa"
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$LEAF_SCRATCH/probe" "$LEAF_SCRATCH/probe.o" "$LEAF_SCRATCH/runtime.o" "$LEAF_ROOT/build/profile_hooks.o"
"$LEAF_SCRATCH/probe"
"$LEAF_COMPILER" -emit obj -O0 -o "$LEAF_SCRATCH/congruence.o" "$LEAF_ROOT/examples/kernel_congruence_runtime.elisa"
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$LEAF_SCRATCH/congruence" "$LEAF_SCRATCH/congruence.o" "$LEAF_SCRATCH/runtime.o" "$LEAF_ROOT/build/profile_hooks.o"
"$LEAF_SCRATCH/congruence"
printf 'strict native kernel leaf, malformed graph, contradiction and congruence controls pass\n'
