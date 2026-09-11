#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_SOURCE="${ELISA_FULL_AUDIT_SOURCE:-src/main.elisa}"
TIME_LIMIT="${ELISA_FULL_AUDIT_TIME_LIMIT:-180}"
RSS_LIMIT_KB="${ELISA_FULL_AUDIT_RSS_LIMIT_KB:-1500000}"

if [[ ! -x "$ROOT_DIR/build/elisa-proof" ]]; then
    printf 'full-source audit failed: build/elisa-proof is missing; run scripts/build.sh first\n' >&2
    exit 2
fi
if [[ ! -f "$ROOT_DIR/$AUDIT_SOURCE" && ! -f "$AUDIT_SOURCE" ]]; then
    printf 'full-source audit failed: source does not exist: %s\n' "$AUDIT_SOURCE" >&2
    exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
    printf 'full-source audit failed: python3 is required for watchdog enforcement\n' >&2
    exit 2
fi

if [[ -n "${ELISA_FULL_AUDIT_DIR:-}" ]]; then
    AUDIT_DIR="$ELISA_FULL_AUDIT_DIR"
    mkdir -p "$AUDIT_DIR"
else
    AUDIT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-full-audit.XXXXXX")"
fi
PROOF_STDOUT="$AUDIT_DIR/proof-report.json"
PROOF_STDERR="$AUDIT_DIR/proof-report.stderr"

# Exit codes are intentionally about the audit harness, not the proof verdict:
#   0 = the proof process completed and emitted valid JSON (inspect report_status)
#   3 = the watchdog stopped it before a complete report was emitted
#   2 = launcher, configuration, or report-format failure
set +e
python3 - "$ROOT_DIR" "$AUDIT_SOURCE" "$TIME_LIMIT" "$RSS_LIMIT_KB" "$PROOF_STDOUT" "$PROOF_STDERR" "$AUDIT_DIR" <<'PY'
import json
import os
import signal
import subprocess
import sys
import time


root, source, time_limit_text, rss_limit_text, stdout_path, stderr_path, audit_dir = sys.argv[1:]
try:
    time_limit = float(time_limit_text)
    rss_limit_kb = int(rss_limit_text)
except ValueError:
    print("full-source audit failed: limits must be numeric", file=sys.stderr)
    raise SystemExit(2)
if time_limit <= 0 or rss_limit_kb <= 0:
    print("full-source audit failed: limits must be positive", file=sys.stderr)
    raise SystemExit(2)

command = [os.path.join(root, "build", "elisa-proof"), "--json", source]
started = time.monotonic()
peak_rss_kb = 0
stop_reason = None

with open(stdout_path, "w", encoding="utf-8") as stdout, open(stderr_path, "w", encoding="utf-8") as stderr:
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
    except OSError as error:
        print(f"full-source audit failed: could not start proof process: {error}", file=sys.stderr)
        raise SystemExit(2)

    while process.poll() is None:
        try:
            rss_text = subprocess.check_output(
                ["ps", "-o", "rss=", "-p", str(process.pid)],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if rss_text:
                peak_rss_kb = max(peak_rss_kb, int(rss_text.split()[0]))
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass

        elapsed = time.monotonic() - started
        if elapsed >= time_limit:
            stop_reason = "time-limit"
            break
        if peak_rss_kb >= rss_limit_kb:
            stop_reason = "rss-limit"
            break
        time.sleep(0.1)

    if stop_reason is not None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    else:
        process.wait()

elapsed = time.monotonic() - started
parsed = None
parse_error = None
try:
    with open(stdout_path, encoding="utf-8") as handle:
        parsed = json.load(handle)
except (OSError, json.JSONDecodeError) as error:
    parse_error = str(error)

result = {
    "audit_directory": audit_dir,
    "command": command,
    "complete": stop_reason is None and parsed is not None,
    "elapsed_seconds": round(elapsed, 2),
    "exit_code": process.returncode,
    "peak_rss_kb": peak_rss_kb,
    "report": stdout_path,
    "report_stderr": stderr_path,
    "report_status": parsed.get("status") if isinstance(parsed, dict) else None,
    "report_verification_state": parsed.get("verification_state") if isinstance(parsed, dict) else None,
    "stop_reason": stop_reason,
    "time_limit_seconds": time_limit,
    "rss_limit_kb": rss_limit_kb,
}
if isinstance(parsed, dict):
    summary = parsed.get("summary")
    if isinstance(summary, dict):
        for key in ("obligations", "proven", "failed"):
            result[key] = summary.get(key)
    replay = parsed.get("replay")
    if isinstance(replay, dict):
        result["replay_gaps"] = replay.get("gaps")
if parse_error is not None:
    result["parse_error"] = parse_error

print(json.dumps(result, indent=2, sort_keys=True))
if stop_reason is not None:
    raise SystemExit(3)
if parsed is None:
    raise SystemExit(2)
raise SystemExit(0)
PY
status=$?
set -e

printf 'full-source audit artifacts: %s\n' "$AUDIT_DIR" >&2
exit "$status"
