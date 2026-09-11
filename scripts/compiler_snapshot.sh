#!/usr/bin/env bash
# Sourced by build.sh and dogfood.sh. Exports the pinned Elisa compiler revision
# into build/snapshot so the proof kernel is compiled against immutable sources.
#
# src/main.elisa (and the executable examples) include the compiler's semantic
# layer through `../../Elisa-compiler/...`. Compiling straight out of the sibling
# working tree meant that any half-finished edit there entered this build. The
# snapshot copies this repository's src/ and examples/ beside a `git archive`
# export of the commit recorded in ELISA_COMPILER_REV, so the relative includes
# resolve to the pinned sources regardless of what the checkout contains. The
# exported profiler hook source is the link boundary for hand-built native
# objects; keeping it in the same snapshot prevents ABI drift between the
# compiler and the proof executable.
#
# Inputs (all optional):
#   ELISA_COMPILER_SRC  compiler git repository (default: ../Elisa-compiler)
#   ELISA_COMPILER_REV  revision override (default: contents of ELISA_COMPILER_REV)
# Outputs:
#   SNAPSHOT_ROOT       directory holding the copied elisa-proof tree
#   SNAPSHOT_COMPILER   directory holding the exported compiler sources

snapshot_fail() {
    printf 'compiler snapshot failed: %s\n' "$1" >&2
    exit 2
}

SNAPSHOT_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPILER_SRC="${ELISA_COMPILER_SRC:-$SNAPSHOT_ROOT_DIR/../Elisa-compiler}"
PINNED_REV="${ELISA_COMPILER_REV:-}"
if [[ -z "$PINNED_REV" ]]; then
    [[ -f "$SNAPSHOT_ROOT_DIR/ELISA_COMPILER_REV" ]] || snapshot_fail "ELISA_COMPILER_REV file is missing"
    PINNED_REV="$(tr -d '[:space:]' < "$SNAPSHOT_ROOT_DIR/ELISA_COMPILER_REV")"
fi
[[ -n "$PINNED_REV" ]] || snapshot_fail "pinned compiler revision is empty"
[[ -d "$COMPILER_SRC" ]] || snapshot_fail "compiler repository not found at $COMPILER_SRC (set ELISA_COMPILER_SRC)"
git -C "$COMPILER_SRC" rev-parse --verify --quiet "${PINNED_REV}^{commit}" >/dev/null \
    || snapshot_fail "revision $PINNED_REV is not a commit in $COMPILER_SRC (fetch it, or update ELISA_COMPILER_REV)"
RESOLVED_REV="$(git -C "$COMPILER_SRC" rev-parse "${PINNED_REV}^{commit}")"

SNAPSHOT_DIR="$SNAPSHOT_ROOT_DIR/build/snapshot"
SNAPSHOT_COMPILER="$SNAPSHOT_DIR/Elisa-compiler"
SNAPSHOT_ROOT="$SNAPSHOT_DIR/elisa-proof"
mkdir -p "$SNAPSHOT_DIR"

# The compiler export is keyed by commit hash; a stale or partial export is
# discarded rather than reused.
if [[ ! -f "$SNAPSHOT_COMPILER/.rev" || "$(cat "$SNAPSHOT_COMPILER/.rev")" != "$RESOLVED_REV" || ! -f "$SNAPSHOT_COMPILER/test/parity/profile_hooks.c" ]]; then
    rm -rf "$SNAPSHOT_COMPILER"
    mkdir -p "$SNAPSHOT_COMPILER"
    git -C "$COMPILER_SRC" archive --format=tar "$RESOLVED_REV" src elisacore_std test/parity/profile_hooks.c \
        | tar -x -C "$SNAPSHOT_COMPILER" \
        || { rm -rf "$SNAPSHOT_COMPILER"; snapshot_fail "git archive of $RESOLVED_REV failed"; }
    printf '%s\n' "$RESOLVED_REV" > "$SNAPSHOT_COMPILER/.rev"
fi

# This repository's own sources are what is being built, so they are refreshed
# from the working tree on every run.
rm -rf "$SNAPSHOT_ROOT"
mkdir -p "$SNAPSHOT_ROOT"
cp -R "$SNAPSHOT_ROOT_DIR/src" "$SNAPSHOT_ROOT/src"
cp -R "$SNAPSHOT_ROOT_DIR/examples" "$SNAPSHOT_ROOT/examples"

export SNAPSHOT_ROOT SNAPSHOT_COMPILER
export ELISA_COMPILER_PINNED_REV="$RESOLVED_REV"
