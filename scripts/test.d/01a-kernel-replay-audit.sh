# Part 1a of the test matrix, sourced after the shared setup. Whole-source kernel replay audit:
# require a coverage floor and all important summaries, and
# classify every budget exhaustion as unsupported rather than silently unknown.
# Peak memory grows with the audited kernel: 1,177,457 KB before the linear-certificate checker
# (C-02/C-03), 1,219,217 KB after it; mocap-cleaner proof tiers and later kernel growth raise it.
KERNEL_REPLAY_AUDIT_MEMORY_LIMIT_KB="${ELISA_KERNEL_REPLAY_AUDIT_MEMORY_LIMIT_KB:-4000000}"
kernel_replay_audit_dir="$standalone_probe_dir/kernel-replay-audit"
kernel_replay_audit_summary="$standalone_probe_dir/kernel-replay-audit-summary.json"
ELISA_FULL_AUDIT_SOURCE="$ROOT_DIR/examples/kernel_replay_standalone.elisa" \
    ELISA_FULL_AUDIT_BINARY="$ROOT_DIR/build/elisa-proof" \
    ELISA_FULL_AUDIT_DIR="$kernel_replay_audit_dir" \
    ELISA_FULL_AUDIT_MEMORY_LIMIT_KB="$KERNEL_REPLAY_AUDIT_MEMORY_LIMIT_KB" \
    python3 "$ROOT_DIR/scripts/report_cache.py" --slot "$ROOT_DIR/examples/kernel_replay_standalone.elisa" -- "$ROOT_DIR/scripts/audit_full_source.sh" >"$kernel_replay_audit_summary"
kernel_replay_audit_status=$?
if [[ "$kernel_replay_audit_status" -eq 3 ]]; then
    python3 - "$kernel_replay_audit_summary" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    audit = json.load(handle)
print(
    "proof test matrix incomplete: standalone replay was stopped by the "
    f"{audit['stop_reason']} watchdog at {audit['peak_memory_kb']}/"
    f"{audit['memory_limit_kb']} KB ({audit['memory_metric']}) after "
    f"{audit['elapsed_seconds']}s; no complete proof report was emitted",
    file=sys.stderr,
)
PY
    exit 1
fi
if [[ "$kernel_replay_audit_status" -ne 0 ]]; then
    printf 'proof test matrix failed: bounded standalone audit harness failed (exit=%s)\n' \
        "$kernel_replay_audit_status" >&2
    exit 1
fi
if ! python3 "$ROOT_DIR/test/validate_kernel_replay_standalone.py" \
    <"$kernel_replay_audit_dir/proof-report.json"; then
    printf 'proof test matrix failed: standalone replay audit coverage or trust boundary regressed\n' >&2
    exit 1
fi
if ! ELISA_PROOF_BIN="$ROOT_DIR/build/elisa-proof" \
    python3 "$ROOT_DIR/scripts/test_typed_literal_summary_coverage.py"; then
    printf 'proof test matrix failed: typed-literal admission summary coverage regressed\n' >&2
    exit 1
fi
