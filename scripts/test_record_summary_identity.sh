#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPILER="${ELISA_COMPILER_BIN:-$ROOT/build/elisac-stage0-a891}"
source "$ROOT/scripts/compiler_provenance.sh"
elisa_verify_stage0_provenance "$COMPILER" "$ROOT"
# Refresh the pinned export and copy the actual proof sources/example together.
# Do not run concurrently with a proof build using this same snapshot.
source "$ROOT/scripts/compiler_snapshot.sh"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/elisa-record-replay.XXXXXX")"
cleanup() {
    rm -f "$WORK/probe.o" "$WORK/probe" "$WORK/build.log"
    rmdir "$WORK"
}
trap cleanup EXIT
"$COMPILER" -emit obj -O0 -o "$WORK/probe.o" "$SNAPSHOT_ROOT/examples/field_equality_runtime.elisa" >"$WORK/build.log" 2>&1 || {
    tail -80 "$WORK/build.log" >&2
    exit 1
}
"${CLANG:-clang}" -Wl,-dead_strip -o "$WORK/probe" "$WORK/probe.o" "$ROOT/build/profile_hooks.o"
"$WORK/probe"
echo 'Exact record summary identity controls pass: nominal type, field names/order/count, nested values, capture-free constructor/update substitution, existing field differential controls'
