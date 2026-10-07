#!/usr/bin/env bash
# Strict AST-level differential test against the former scalar-witness scan.
set -euo pipefail
MARKER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$MARKER_ROOT/scripts/compiler_provenance.sh"
source "$MARKER_ROOT/scripts/link_flags.sh"
MARKER_COMPILER="$(elisa_default_stage0 "$MARKER_ROOT")" || { printf 'pinned stage0 compiler not found\n' >&2; exit 2; }
if ! elisa_compiler_is_stage0 "$MARKER_COMPILER"; then
    printf 'this differential test requires the pinned stage0 compiler\n' >&2
    exit 2
fi
elisa_verify_stage0_provenance "$MARKER_COMPILER" "$MARKER_ROOT"
MARKER_FIXTURE="$MARKER_ROOT/build/snapshot/elisa-proof/examples/marker_dispatch_runtime.elisa"
cmp "$MARKER_ROOT/examples/marker_dispatch_runtime.elisa" "$MARKER_FIXTURE"
cmp "$MARKER_ROOT/src/proof/linear/witnessed_expressions.elisa" "$MARKER_ROOT/build/snapshot/elisa-proof/src/proof/linear/witnessed_expressions.elisa"
MARKER_SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/elisa-scalar-marker.XXXXXX")"
cleanup_marker() {
    rm -f -- "$MARKER_SCRATCH/probe.o" "$MARKER_SCRATCH/probe"
    rmdir -- "$MARKER_SCRATCH"
}
trap cleanup_marker EXIT
"$MARKER_COMPILER" -emit obj -O0 -o "$MARKER_SCRATCH/probe.o" "$MARKER_FIXTURE"
"${CLANG:-clang}" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$MARKER_SCRATCH/probe" "$MARKER_SCRATCH/probe.o" "$MARKER_ROOT/build/profile_hooks.o"
"$MARKER_SCRATCH/probe"
printf 'strict scalar-marker dispatch matches original parsers for mixed and singleton contexts\n'
