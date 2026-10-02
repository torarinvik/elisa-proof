#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# O2 by default: the checker spends its time in tight term-comparison loops, and on the
# mocap-cleaner corpus the O2 build gives identical reports in a fraction of the O0 time.
# ELISA_OPT_LEVEL=O0 still gives a debug build.
OPT_LEVEL="${ELISA_OPT_LEVEL:-O2}"
COMPILE_MODE="${ELISA_PROOF_COMPILE_MODE:-strict}"
CONTRACT_FLAG=""
case "$COMPILE_MODE" in
    strict) ;;
    runtime-checks) CONTRACT_FLAG="-permissive" ;;
    *) printf 'ELISA_PROOF_COMPILE_MODE must be strict or runtime-checks\n' >&2; exit 2 ;;
esac
case "$OPT_LEVEL" in
    O0|O1|O2|O3) ;;
    *) printf 'ELISA_OPT_LEVEL must be O0, O1, O2, or O3 (got %s)\n' "$OPT_LEVEL" >&2; exit 2 ;;
esac
# stage1 stops a compile past its runaway guard (4 GiB by default). The whole tool links the
# compiler front end, and its compile now peaks between 3.6 and 4.2 GB (2026-09-28, O0 through
# O3), so give it headroom unless the caller set a limit.
export ELISA_STAGE1_MAX_RSS_KB="${ELISA_STAGE1_MAX_RSS_KB:-8388608}"
PROOF_OUTPUT="${ELISA_PROOF_OUTPUT:-$ROOT_DIR/build/elisa-proof}"
# The entry point, relative to the repository: `src/replay_main.elisa` builds the portable
# package checker `elisa-proof-replay` from the same snapshot.
PROOF_MAIN="${ELISA_PROOF_MAIN:-src/main.elisa}"
case "$PROOF_MAIN" in
    src/main.elisa|src/replay_main.elisa) ;;
    *) printf 'ELISA_PROOF_MAIN must be src/main.elisa or src/replay_main.elisa (got %s)\n' "$PROOF_MAIN" >&2; exit 2 ;;
esac
COMPILER="${ELISA_COMPILER_BIN:-}"
# shellcheck source=scripts/compiler_provenance.sh
source "$ROOT_DIR/scripts/compiler_provenance.sh"

if [[ -z "$COMPILER" ]]; then
    # Prefer the source checkout's freshness-guarded stage1 wrapper over an
    # installed snapshot, then use the pinned/current Go bootstrap as fallback.
    COMPILER="$(elisa_default_stage1 "$ROOT_DIR" || true)"
    if [[ -z "$COMPILER" ]]; then
        COMPILER="$(elisa_default_stage0 "$ROOT_DIR" || true)"
    fi
    if [[ -z "$COMPILER" ]]; then
        COMPILER="$(command -v elisac 2>/dev/null || true)"
    fi
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
driver="$(grep -o '/[^"]*/scripts/elisac_stage1\.sh' "$COMPILER" 2>/dev/null | head -1 || true)"
if [[ -z "$driver" && "$(basename "$COMPILER")" == "elisac_stage1.sh" ]]; then
    driver="$COMPILER"
fi
if [[ -n "$driver" ]]; then
    COMPILER_IS_STAGE1=1
    if [[ -z "$RUNTIME_OBJ" ]]; then
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
mkdir -p "$(dirname -- "$PROOF_OUTPUT")"
BUILD_LOCK="$ROOT_DIR/build/.elisa-proof-build.lock"
if ! mkdir "$BUILD_LOCK" 2>/dev/null; then
    lock_owner="unknown"
    [[ -f "$BUILD_LOCK/pid" ]] && lock_owner="$(<"$BUILD_LOCK/pid")"
    printf 'another proof build owns %s (pid %s); wait for it to finish before building again\n' \
        "$BUILD_LOCK" "$lock_owner" >&2
    exit 2
fi
printf '%s\n' "$$" >"$BUILD_LOCK/pid"

BUILD_TOKEN="$$"
STAGE_OBJECT="$ROOT_DIR/build/elisa-proof-stage.$BUILD_TOKEN.o"
PROOF_BINARY="$ROOT_DIR/build/elisa-proof.$BUILD_TOKEN"
DEFAULT_PROFILE_HOOKS_OBJ="$ROOT_DIR/build/profile_hooks.o"
PROFILE_HOOKS_OBJ="${ELISA_PROFILE_HOOKS_OBJ:-$DEFAULT_PROFILE_HOOKS_OBJ}"
PROFILE_HOOKS_TEMP="$ROOT_DIR/build/profile_hooks.$BUILD_TOKEN.o"

cleanup_build() {
    rm -f "$STAGE_OBJECT" "$PROOF_BINARY" "$PROOF_BINARY.manifest.json" "$PROFILE_HOOKS_TEMP" "$BUILD_LOCK/pid"
    rmdir "$BUILD_LOCK" 2>/dev/null || true
}
trap cleanup_build EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

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
if [[ ! -f "$PROFILE_HOOKS_SOURCE" ]]; then
    printf 'missing profiler ABI hook source: %s\n' "$PROFILE_HOOKS_SOURCE" >&2
    exit 2
fi
if [[ ! -f "$PROFILE_HOOKS_OBJ" || "$PROFILE_HOOKS_SOURCE" -nt "$PROFILE_HOOKS_OBJ" ]]; then
    clang -c -O2 -o "$PROFILE_HOOKS_TEMP" "$PROFILE_HOOKS_SOURCE"
    mv -f "$PROFILE_HOOKS_TEMP" "$PROFILE_HOOKS_OBJ"
fi
if [[ -n "$CONTRACT_FLAG" ]]; then
    "$COMPILER" "$CONTRACT_FLAG" -emit obj "-$OPT_LEVEL" -o "$STAGE_OBJECT" "$SNAPSHOT_ROOT/$PROOF_MAIN"
else
    "$COMPILER" -emit obj "-$OPT_LEVEL" -o "$STAGE_OBJECT" "$SNAPSHOT_ROOT/$PROOF_MAIN"
fi
LINK_INPUTS=("$STAGE_OBJECT" "$PROFILE_HOOKS_OBJ")
[[ -n "$RUNTIME_OBJ" ]] && LINK_INPUTS+=("$RUNTIME_OBJ")
clang -Wl,-dead_strip -o "$PROOF_BINARY" "${LINK_INPUTS[@]}"
# Sign before hashing so the manifest digest names the exact executable that runs.
if [[ "$(uname -s)" == "Darwin" ]] && command -v codesign >/dev/null 2>&1; then
    codesign -s - --force "$PROOF_BINARY" 2>/dev/null
fi
if [[ "$PROOF_MAIN" == "src/main.elisa" ]]; then
    mv -f "$STAGE_OBJECT" "$ROOT_DIR/build/elisa-proof-stage.o"
else
    rm -f "$STAGE_OBJECT"
fi
MANIFEST_TEMP="$PROOF_BINARY.manifest.json"
COMPILER_PRODUCT="$COMPILER"
if [[ -n "${stage1_root:-}" && -x "${ELISA_STAGE1_BIN:-$stage1_root/bin/elisac-stage1}" ]]; then
    COMPILER_PRODUCT="${ELISA_STAGE1_BIN:-$stage1_root/bin/elisac-stage1}"
fi
python3 "$ROOT_DIR/scripts/build_manifest.py" \
    --binary "$PROOF_BINARY" \
    --compiler "$COMPILER" \
    --compiler-product "$COMPILER_PRODUCT" \
    --compiler-root "${stage1_root:-}" \
    --stage "$([[ "$COMPILER_IS_STAGE1" -eq 1 ]] && echo stage1 || echo stage0)" \
    --stage1-revision "${stage1_revision:-}" \
    --runtime "${RUNTIME_OBJ:-}" \
    --profile-hooks "$PROFILE_HOOKS_OBJ" \
    --frontend-repo "$COMPILER_SRC" \
    --frontend-revision "$RESOLVED_REV" \
    --proof-root "$ROOT_DIR" \
    --snapshot-root "$SNAPSHOT_ROOT" \
    --opt-level "$OPT_LEVEL" \
    --compile-mode "$COMPILE_MODE" \
    --contract-flag "$CONTRACT_FLAG" \
    --installed-as "$PROOF_OUTPUT" \
    --output "$MANIFEST_TEMP"
mv -f "$PROOF_BINARY" "$PROOF_OUTPUT"
mv -f "$MANIFEST_TEMP" "$PROOF_OUTPUT.manifest.json"
