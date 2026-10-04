#!/usr/bin/env bash
# Bounded, source-aware profiling of elisa-proof using the native elisa-profiler.
# Run from any directory after the native profiler toolchain is ready.
# ELISA_PROFILER may name the profiler executable; ELISA_PROFILE_OUT selects the output root.
# Native capture is validated on macOS and x86_64 Linux. Windows needs its own
# native backend and test host; do not treat a POSIX compatibility layer as support.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILER="${ELISA_PROFILER:-$ROOT/../elisa-profiler/bin/elisa-profiler}"
OUT_ROOT="${ELISA_PROFILE_OUT:-$ROOT/build/luna-profile}"
# The proof checker includes the compiler frontend; its instrumented O2 compile
# exceeds the profiler's normal five-minute tool bound on the Linux host.
export ELISA_PROFILER_TOOL_TIMEOUT_SECONDS="${ELISA_PROFILER_TOOL_TIMEOUT_SECONDS:-1200}"
export ELISA_PROFILER_MAX_PROGRAM_OUTPUT_BYTES="${ELISA_PROFILER_MAX_PROGRAM_OUTPUT_BYTES:-16777216}"

fail() {
    printf 'luna profile: %s\n' "$1" >&2
    exit 2
}

HOST_OS="$(uname -s)"
case "$HOST_OS" in
    Darwin) ;;
    Linux)
        [[ "$(uname -m)" == x86_64 ]] || fail "Linux profiling is currently validated on x86_64 only"
        export ELISA_HOST_LINUX=1 ELISA_HOST_X86_64=1
        ;;
    *) fail "unsupported native profiler host $HOST_OS; Windows support is deferred until native validation is available" ;;
esac

[[ -x "$PROFILER" ]] || fail "profiler executable not found: $PROFILER (set ELISA_PROFILER)"
[[ -f "$ROOT/src/main.elisa" ]] || fail "proof entry source is missing"
[[ -f "$ROOT/examples/symbolic_quantifier.elisa" ]] || fail "symbolic quantifier workload is missing"
[[ -f "$ROOT/examples/congruence.elisa" ]] || fail "congruence workload is missing"
[[ -f "$ROOT/examples/rejected_congruence.elisa" ]] || fail "congruence refusal workload is missing"
command -v timeout >/dev/null 2>&1 || fail "GNU timeout is required for the overall run bound"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for workload provenance"
command -v python3 >/dev/null 2>&1 || fail "python3 is required to validate captured proof reports"

REV="$(git -C "$ROOT" rev-parse --verify HEAD)"
REV_SHORT="${REV:0:12}"
mkdir -p "$OUT_ROOT"
RUN_DIR="$(mktemp -d "$OUT_ROOT/luna-$REV_SHORT.XXXXXX")"
BUILD_CACHE="${ELISA_PROFILE_BUILD_CACHE:-$RUN_DIR/build-cache}"

{
    printf 'purpose=source-aware profiling of elisa-proof CLI\n'
    printf 'proof_root=%s\n' "$ROOT"
    printf 'proof_revision=%s\n' "$REV"
    printf 'proof_worktree_status=\n'
    git -C "$ROOT" status --short --untracked-files=all -- src examples
    printf 'profiler=%s\n' "$PROFILER"
    printf 'host_os=%s\nhost_architecture=%s\n' "$HOST_OS" "$(uname -m)"
    printf 'profiler_sha256='
    sha256sum "$PROFILER" | awk '{print $1}'
    printf 'collection_mode=sample\nsample_period_us=1000\noptimization_level=-O2\n'
    printf 'repetitions=3\nwarmups=0\ntarget_timeout_seconds=120\noverall_timeout_seconds=1800\n'
    printf 'tool_timeout_seconds=%s\n' "$ELISA_PROFILER_TOOL_TIMEOUT_SECONDS"
    printf 'program_output_byte_limit=%s\n' "$ELISA_PROFILER_MAX_PROGRAM_OUTPUT_BYTES"
    printf 'build_cache=%s\n' "$BUILD_CACHE"
    printf 'target_instrumentation=profiler compiles the Elisa target with function tracing and debug source information\n'
    printf 'sampling_caveat=CPU samples retain instrumented Elisa call stacks; they are not native instruction-pointer samples or exact invocation counts\n'
    printf 'attribution_caveat=runtime, foreign, and optimized-away frames are not unwound; their work can be charged to an instrumented Elisa caller\n'
    printf 'overhead_caveat=trace instrumentation changes execution cost, so these captures locate hotspots and do not establish uninstrumented throughput or speedups\n'
} > "$RUN_DIR/README.txt"

profile_case() {
    local label="$1"
    local workload="$2"
    local expected_status="$3"
    local expected_exit="$4"
    local expected_refusals="${5:-}"
    local expected_capture_outcome="success"
    local report="$RUN_DIR/$label.json"

    [[ "$expected_exit" -eq 0 ]] || expected_capture_outcome="target_exit"

    {
        printf '\ncase=%s\nworkload=%s\nexpected_proof_status=%s\nexpected_target_exit=%s\nexpected_refusals=%s\nworkload_sha256=' "$label" "$workload" "$expected_status" "$expected_exit" "${expected_refusals:-none}"
        sha256sum "$ROOT/$workload" | awk '{print $1}'
    } >> "$RUN_DIR/README.txt"

    set +e
    (
        cd "$ROOT"
        timeout --signal=TERM --kill-after=15s 1800s \
            "$PROFILER" profile "$ROOT/src/main.elisa" \
            --mode sample --sample-period-us 1000 \
            --repeat 3 --warmup 0 -O2 \
            --timeout 120 --max-capture-bytes 67108864 \
            --max-artifact-bytes 134217728 \
            --cache-dir "$BUILD_CACHE" \
            --path-map "$ROOT=elisa-proof" \
            --format json --output "$report" \
            -- --json "$workload"
    )
    local profile_status=$?
    set -e
    [[ "$profile_status" -eq "$expected_exit" ]] || fail "$label capture returned $profile_status; expected target exit $expected_exit (overall timeout is 124)"
    [[ -s "$report" ]] || fail "$label capture did not produce a JSON report"
    python3 - "$report" "$expected_capture_outcome" "$expected_status" "$expected_exit" "$expected_refusals" <<'PY'
import json
import sys

def require(condition, message):
    if not condition:
        raise SystemExit(f"profile validation failed: {message}")

path, expected_outcome, expected_status, expected_exit, expected_refusals = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    capture = json.load(stream)
run = capture.get("run", {})
require(run.get("outcome") == expected_outcome,
        f"{path}: outcome {run.get('outcome')!r}, expected {expected_outcome!r}")
require(run.get("exit_code") == int(expected_exit),
        f"{path}: target exit {run.get('exit_code')!r}, expected {expected_exit}")
require(run.get("collection_mode") == "sample",
        f"{path}: collection mode {run.get('collection_mode')!r}")
require(run.get("requested_repetitions") == 3,
        f"{path}: requested repetitions {run.get('requested_repetitions')!r}")
require(run.get("completed_repetitions") == 3,
        f"{path}: completed repetitions {run.get('completed_repetitions')!r}")
expected_failed = 0 if int(expected_exit) == 0 else 3
require(run.get("failed_repetitions") == expected_failed,
        f"{path}: failed repetitions {run.get('failed_repetitions')!r}, expected {expected_failed}")
require(capture.get("program_stdout_truncated") is False,
        f"{path}: target JSON output was truncated")
stdout = capture.get("program_stdout", "")
decoder = json.JSONDecoder()
proof_reports = []
cursor = 0
while cursor < len(stdout):
    while cursor < len(stdout) and stdout[cursor].isspace():
        cursor += 1
    if cursor == len(stdout):
        break
    proof, cursor = decoder.raw_decode(stdout, cursor)
    proof_reports.append(proof)
require(len(proof_reports) == 3,
        f"{path}: decoded {len(proof_reports)} proof reports, expected 3")
for proof in proof_reports:
    require(proof.get("status") == expected_status,
            f"{path}: proof status {proof.get('status')!r}, expected {expected_status!r}")
    replay = proof.get("replay", {})
    require(replay.get("gaps") == 0,
            f"{path}: replay gap count {replay.get('gaps')!r}")
    require(replay.get("certificates") == replay.get("replayed"),
            f"{path}: certificate and replay counts differ")
    require(all(not goal.get("proven") or goal.get("replay_status") == "replayed"
                for goal in proof.get("goals", [])),
            f"{path}: a proven goal lacks replay confirmation")
refusals = set(expected_refusals.split())
if refusals:
    for proof in proof_reports:
        require(proof.get("summary", {}).get("semantic_errors") == 0,
                f"{path}: refusal workload had semantic errors")
        findings = {item.get("name") for item in proof.get("findings", [])}
        claimed = {item.get("name") for item in proof.get("goals", [])
                   if item.get("proven") and item.get("rule") != "resource-safety"}
        require(refusals <= findings,
                f"{path}: expected refusal findings missing: {sorted(refusals - findings)}")
        require(not (refusals & claimed),
                f"{path}: refused goals were claimed proven: {sorted(refusals & claimed)}")
PY
}

printf 'run_dir=%s\n' "$RUN_DIR"
profile_case symbolic-quantifier examples/symbolic_quantifier.elisa proved 0
profile_case congruence examples/congruence.elisa proved 0
profile_case congruence-refusal examples/rejected_congruence.elisa failed 1 \
    'disequality_premise order_premise disjunctive_premise unrelated_operand distinct_former struct_equality_premise local_struct_equality_premise constructed_aggregate cross_width wrapping_operand'
printf 'profiles=complete\nreports=%s/symbolic-quantifier.json,%s/congruence.json,%s/congruence-refusal.json\n' "$RUN_DIR" "$RUN_DIR" "$RUN_DIR"
