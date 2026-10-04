# shellcheck shell=bash
# Sourced by the proof matrix after its report-cache variables are initialized.
# Buffer JSON probes so a valid-looking report cannot hide a crash or an exit/verdict mismatch.
# The downstream assertions still check the report's expected shape; this adapter checks that the
# whole JSON document parsed and that the verifier's process exit agrees with its top-level verdict.
run_json_report() {
    local source_path="$1"
    local report_path
    local proof_status
    local expected_status

    if ! report_path="$(mktemp "${TMPDIR:-/tmp}/elisa-proof-json-probe.XXXXXX")"; then
        printf 'proof test matrix failed: could not allocate a report buffer for %s\n' "$source_path" >&2
        return 98
    fi
    local cache_key=""
    if [[ -n "$REPORT_CACHE" ]]; then
        cache_key="$REPORT_CACHE/$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$source_path" | tr -d '\n' | shasum | cut -d' ' -f1)"
        # Wait for a prefetched fixture's entry while the prefetcher still runs.
        while [[ ! -f "$cache_key.rc" ]] && [[ -n "$REPORT_PREFETCH_PID" ]] && kill -0 "$REPORT_PREFETCH_PID" 2>/dev/null; do
            sleep 1  # poll-ok: local file from our own prefetcher
            grep -qF "\"\$ROOT_DIR/${source_path#"$ROOT_DIR/"}\"" "$ROOT_DIR/scripts/test.sh" || break
        done
    fi
    if [[ -n "$cache_key" && -f "$cache_key.rc" ]]; then
        cp "$cache_key.json" "$report_path"
        proof_status="$(cat "$cache_key.rc")"
    elif "$ROOT_DIR/build/elisa-proof" --json "$source_path" >"$report_path"; then
        proof_status=0
    else
        proof_status=$?
    fi
    if ! expected_status="$(python3 - "$report_path" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
status = report.get("status")
if status == "proved":
    print(0)
elif status == "failed":
    print(1)
else:
    raise SystemExit(f"unexpected --json verdict: {status!r}")
PY
)"; then
        printf 'proof test matrix failed: verifier emitted an incomplete or malformed JSON report for %s (exit=%s)\n' "$source_path" "$proof_status" >&2
        rm -f "$report_path"
        return 98
    fi
    if [[ "$proof_status" -ne "$expected_status" ]]; then
        printf 'proof test matrix failed: verifier exit/report mismatch for %s (exit=%s verdict-exit=%s)\n' "$source_path" "$proof_status" "$expected_status" >&2
        rm -f "$report_path"
        return 97
    fi
    if ! cat "$report_path"; then
        printf 'proof test matrix failed: could not forward the complete JSON report for %s\n' "$source_path" >&2
        rm -f "$report_path"
        return 99
    fi
    rm -f "$report_path"
    return "$expected_status"
}
