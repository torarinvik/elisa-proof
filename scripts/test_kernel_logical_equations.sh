#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPILER="${ELISA_COMPILER_BIN:-$ROOT/build/elisac-stage0-a891}"
source "$ROOT/scripts/compiler_provenance.sh"
elisa_verify_stage0_provenance "$COMPILER" "$ROOT"
REV="$(tr -d '[:space:]' < "$ROOT/ELISA_COMPILER_REV")"
if [[ ! -f "$ROOT/build/snapshot/Elisa-compiler/.rev" ]] || [[ "$(<"$ROOT/build/snapshot/Elisa-compiler/.rev")" != "$REV"* ]]; then
    printf 'build the pinned proof snapshot before running this regression\n' >&2
    exit 2
fi
WORK="$(mktemp -d "${TMPDIR:-/tmp}/elisa-kernel-logical.XXXXXX")"
cleanup() {
    rm -f -- "$WORK/runtime.o" "$WORK/probe.o" "$WORK/probe"
    rmdir -- "$WORK"
}
trap cleanup EXIT
"$COMPILER" -emit obj -O0 -o "$WORK/runtime.o" "$ROOT/build/snapshot/Elisa-compiler/elisacore_std/native_runtime_support.elisa"
"$COMPILER" -emit obj -O0 -o "$WORK/probe.o" "$ROOT/examples/kernel_logical_equations_runtime.elisa"
"${CLANG:-clang}" -Wl,-dead_strip -o "$WORK/probe" "$WORK/probe.o" "$WORK/runtime.o" "$ROOT/build/profile_hooks.o"
"$WORK/probe"
echo 'logical Boolean equation kernel controls pass: constant absorption, polarity, mirrored inequality, integer/unwitnessed leaves, malformed literals, node bounds and cycles'
