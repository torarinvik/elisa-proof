#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-optimized-replay.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM HUP

for level in O2 O3; do
    proof_binary="$WORK_DIR/elisa-proof-$level"
    ELISA_OPT_LEVEL="$level" ELISA_PROOF_OUTPUT="$proof_binary" "$ROOT_DIR/scripts/build.sh"
    for fixture in verified sum_bound dogfood_kernel_core; do
        report_path="$WORK_DIR/$level-$fixture.json"
        if ! "$proof_binary" --json "$ROOT_DIR/examples/$fixture.elisa" >"$report_path"; then
            printf 'optimized proof replay failed: %s rejected %s\n' "$level" "$fixture" >&2
            exit 1
        fi
        python3 - "$report_path" "$level" "$fixture" <<'PY'
import json
import sys

path, level, fixture = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    report = json.load(handle)

assert report["status"] == "proved", (level, fixture, report.get("status"))
assert report["replay"]["gaps"] == 0, (level, fixture, report["replay"])
assert report["replay"]["certificates"] == report["replay"]["replayed"]
for goal in report["goals"]:
    if goal["proven"]:
        assert goal["replay_status"] == "replayed", (level, fixture, goal)
PY
    done
done

printf 'optimized replay checks passed at O2 and O3\n'
