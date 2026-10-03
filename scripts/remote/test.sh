#!/usr/bin/env bash
# Sync, cross-build, and run scripts/test.sh remotely with every fixture and Python test
# prefetched in parallel. The Mac only cross-compiles; $ELISA_REMOTE_HOST (default winpc) links;
# the suite runs on $ELISA_TEST_HOST (default: the link host), reached on $ELISA_TEST_PORT.
# A test host needs clang-19/llvm-19-dev and ~/work/Elisa-compiler (pinned rev, runtime built).
# Usage: scripts/remote/test.sh [jobs]   Log: $ELISA_REMOTE_WORK/test.log; exits with test.sh's status.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${ELISA_REMOTE_HOST:-winpc}"
TEST_HOST="${ELISA_TEST_HOST:-$HOST}"
TEST_PORT="${ELISA_TEST_PORT:-}"
WORK="${ELISA_REMOTE_WORK:-${TMPDIR:-/tmp}/elisa-proof-remote-build}"
TSSH=(ssh -o BatchMode=yes -o LogLevel=ERROR ${TEST_PORT:+-p "$TEST_PORT"} "$TEST_HOST")
# The full-source audit watchdog is a runaway guard; slow hosts (winpc's WSL) need more than 180 s.
AUDIT_LIMIT="${ELISA_FULL_AUDIT_TIME_LIMIT:-$([[ "$TEST_HOST" == winpc ]] && echo 600 || echo 180)}"
# winpc cannot compile the prover natively (OOM), so its run skips the optimized-build gate.
SKIP_OPTIMIZED="${ELISA_PROOF_SKIP_OPTIMIZED:-$([[ "$TEST_HOST" == winpc ]] && echo 1 || echo 0)}"
JOBS="${1:-$("${TSSH[@]}" 'cd ~/work/elisa-proof 2>/dev/null && python3 scripts/report_cache.py --cpus || nproc' 2>/dev/null || echo 12)}"
mkdir -p "$WORK"
T0=$(date +%s); step() { echo "[$(( $(date +%s) - T0 ))s] $*"; }
step sync
bash "$DIR/sync.sh" "$HOST" & sync_pid=$!
if [[ "$TEST_HOST" != "$HOST" ]]; then bash "$DIR/sync.sh" "$TEST_HOST" "$TEST_PORT" || exit 1; fi
wait "$sync_pid" || exit 1
step build; bash "$DIR/build.sh" | tail -2; [[ ${PIPESTATUS[0]} -eq 0 ]] || exit 1
if [[ "$TEST_HOST" != "$HOST" ]]; then
    step ship
    rm -rf "$WORK/ship"; mkdir -p "$WORK/ship"
    rsync -az "$HOST:work/elisa-proof/build/" "$WORK/ship/" || exit 1
    rsync -az -e "ssh -o BatchMode=yes -o LogLevel=ERROR${TEST_PORT:+ -p $TEST_PORT}" "$WORK/ship/" "$TEST_HOST:work/elisa-proof/build/" || exit 1
fi
step "test (jobs=$JOBS on $TEST_HOST)"
"${TSSH[@]}" "cd ~/work/elisa-proof && export ELISA_STAGE1_MAX_RSS_KB=\${ELISA_STAGE1_MAX_RSS_KB:-16777216} GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=\$HOME/work/Elisa-compiler LLVM_CONFIG=/usr/lib/llvm-19/bin/llvm-config PATH=\$HOME/work/Elisa-compiler/tools/linux_shim:\$PATH && ELISA_PROOF_SKIP_BUILD=1 ELISA_PROOF_JOBS=$JOBS ELISA_FULL_AUDIT_TIME_LIMIT=$AUDIT_LIMIT ELISA_PROOF_SKIP_OPTIMIZED=$SKIP_OPTIMIZED bash scripts/test.sh > /tmp/elisa-proof-test.log 2>&1; echo test=\$? >> /tmp/elisa-proof-test.log"
scp -q ${TEST_PORT:+-P "$TEST_PORT"} -o LogLevel=ERROR "$TEST_HOST:/tmp/elisa-proof-test.log" "$WORK/test.log"
step done
tail -5 "$WORK/test.log"
grep -q '^test=0$' "$WORK/test.log"
