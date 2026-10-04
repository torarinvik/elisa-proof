#!/usr/bin/env bash
set -euo pipefail

# KEEP_GOING=1 runs every step and reports all failures instead of stopping at the first.
# A failing step is one that would have stopped the run: a command failing under `set -e`
# or an `exit` with a nonzero status. The run still exits 1 if any step failed; only
# the stopping changes, never what a step checks.
KEEP_GOING="${KEEP_GOING:-0}"
keep_going_failures=0
if [[ "$KEEP_GOING" == 1 && "${BASH_VERSINFO[0]}" -lt 4 ]]; then
    # bash 3.2 (macOS /bin/bash) overwrites PIPESTATUS when the ERR trap below runs,
    # so rerun under a newer bash.
    for keep_going_bash in /opt/homebrew/bin/bash /usr/local/bin/bash; do
        [[ -x "$keep_going_bash" ]] && exec "$keep_going_bash" "$0" "$@"
    done
    printf 'KEEP_GOING=1 needs bash 4 or newer\n' >&2
    exit 2
fi
if [[ "$KEEP_GOING" == 1 ]]; then
    # Counts a failing command only while `set -e` is wanted. bash 4+ keeps PIPESTATUS intact
    # across the trap, so a `set +e` block still reads the statuses of an expected failure.
    keep_going_errexit=1
    set() {
        local arg
        local args=()
        for arg in "$@"; do
            case "$arg" in
                -e) keep_going_errexit=1 ;;
                +e) keep_going_errexit=0 ;;
                *) args+=("$arg") ;;
            esac
        done
        if [[ ${#args[@]} -gt 0 ]]; then builtin set "${args[@]}"; fi
        return 0
    }
    exit() {
        local status="${1:-$?}"
        if [[ "$status" -eq 0 ]]; then builtin exit 0; fi
        keep_going_failures=$((keep_going_failures + 1))
        printf 'KEEP_GOING: step failed (status %s) at line %s\n' "$status" "${BASH_LINENO[0]}" >&2
        return 0
    }
    builtin set +e
    trap 'if [[ "$keep_going_errexit" -eq 1 ]]; then keep_going_failures=$((keep_going_failures + 1)); printf "KEEP_GOING: command failed at line %s\n" "$LINENO" >&2; fi' ERR
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/link_flags.sh
source "$ROOT_DIR/scripts/link_flags.sh"
# Per-run scratch space: several checkouts may run this suite on one shared host. Every later
# temporary path is added to TEST_CLEANUP rather than replacing the EXIT trap.
ELISA_TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-test-run.XXXXXX")"
export ELISA_TEST_TMP
TEST_CLEANUP=("$ELISA_TEST_TMP")
test_cleanup() { rm -rf "${TEST_CLEANUP[@]}"; }
trap test_cleanup EXIT
# The matrix runs as ordered parts sourced into this shell, so state (set -e/+e, traps,
# variables such as SELF_HOST_COMPILER and the helper run_json_report) carries across them.
# Each part stays under the 600-line source boundary that check_source_length.py enforces.
for test_part in "$ROOT_DIR"/scripts/test.d/[0-9][0-9]*.sh; do
    # shellcheck source=/dev/null
    source "$test_part"
done
