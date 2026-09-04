#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPILER="${ELISA_COMPILER_BIN:-}"
if [[ -z "$COMPILER" ]]; then
    # `elisac` was a symlink to the Go compiler and is gone; the stage names are
    # explicit now. Prefer the self-hosted compiler. Its objects need the runtime
    # object discovered below; stage0 remains a supported fallback.
    for candidate in elisac-stage1 elisac-stage0 elisac; do
        COMPILER="$(command -v "$candidate" 2>/dev/null || true)"
        [[ -n "$COMPILER" ]] && break
    done
fi
if [[ -z "$COMPILER" ]]; then
    printf 'dogfood failed: set ELISA_COMPILER_BIN to an Elisa compiler\n' >&2
    exit 1
fi

# A stage1 wrapper emits objects that use the self-hosted runtime. Keep this in
# sync with build.sh so the executable dogfood harness exercises the same product
# configuration as the proof binary itself.
RUNTIME_OBJ="${ELISA_RUNTIME_OBJ:-}"
if [[ -z "$RUNTIME_OBJ" ]]; then
    driver="$(grep -o '/[^\"]*/scripts/elisac_stage1\.sh' "$COMPILER" 2>/dev/null | head -1 || true)"
    if [[ -n "$driver" ]]; then
        candidate="${driver%/scripts/elisac_stage1.sh}/build/runtime/elisacore_runtime.o"
        [[ -f "$candidate" ]] && RUNTIME_OBJ="$candidate"
    fi
fi

"$ROOT_DIR/scripts/build.sh"

REPORT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-dogfood.XXXXXX")"
trap 'rm -rf "$REPORT_DIR"' EXIT

run_probe() {
    local label="$1"
    local source="$2"
    local expected_status="$3"
    local output="$REPORT_DIR/$label.json"
    local repeat_output="$REPORT_DIR/$label.repeat.json"
    set +e
    "$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/$source" >"$output"
    local actual_status=$?
    set -e
    if [[ "$actual_status" -ne "$expected_status" ]]; then
        printf 'dogfood failed: %s exited %s (expected %s)\n' "$label" "$actual_status" "$expected_status" >&2
        return 1
    fi
    set +e
    "$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/$source" >"$repeat_output"
    local repeat_status=$?
    set -e
    if [[ "$repeat_status" -ne "$expected_status" ]]; then
        printf 'dogfood failed: %s changed exit status on repeat (%s vs %s)\n' "$label" "$repeat_status" "$expected_status" >&2
        return 1
    fi
    if ! cmp -s "$output" "$repeat_output"; then
        printf 'dogfood failed: %s produced a non-deterministic proof report\n' "$label" >&2
        return 1
    fi
    python3 - "$label" "$output" <<'PY'
import json
import sys

label, path = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    report = json.load(handle)

replay = report["replay"]
if replay["gaps"] != 0 or replay["certificates"] != replay["replayed"]:
    raise SystemExit(f"dogfood failed: {label} has certificate replay gaps")
if report["kernel"]["independent_replay"] is not True:
    raise SystemExit(f"dogfood failed: {label} did not use independent kernel replay")
print(f"dogfood {label}: status={report['status']} obligations={report['summary']['obligations']} proven={report['summary']['proven']} replay_gaps=0")
PY
}

# These are the currently formalized, source-neutral slices. They must be fully proved and
# independently replayed; no AST-backed checker result is substituted for this evidence.
run_probe kernel_core src/proof/kernel_core.elisa 0
run_probe kernel_core_fixture examples/dogfood_kernel_core.elisa 0

# This fixture intentionally contains unsupported surface around the standalone replay module.
# A non-zero command verdict is expected, but every certificate it does emit must replay.
run_probe replay_standalone examples/kernel_replay_standalone.elisa 1
run_probe arena_cycle_rejected examples/rejected_kernel_arena_cycle.elisa 1
run_probe borrow_four_nested_fields examples/borrow_four_nested_fields.elisa 0
run_probe rejected_borrow_four_nested_alias examples/rejected_borrow_four_nested_alias.elisa 1
run_probe borrow_indexed_places examples/borrow_indexed_places.elisa 0
run_probe rejected_borrow_index_alias examples/rejected_borrow_index_alias.elisa 1

# Exercise the same admission routine as native Elisa code. This is separate from the report
# checker: malformed input must be rejected by the compiled source-neutral module too.
runtime_dir="$REPORT_DIR/runtime-arena"
mkdir -p "$runtime_dir"
runtime_source="$ROOT_DIR/../Elisa-compiler/elisacore_std/native_runtime_support.elisa"
if [[ ! -f "$runtime_source" ]]; then
    printf 'dogfood failed: Elisa runtime source is missing for executable arena harness\n' >&2
    exit 1
fi
"$COMPILER" -emit obj -O0 -o "$runtime_dir/program.o" "$ROOT_DIR/examples/kernel_arena_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/program" "$runtime_dir/program.o" "$RUNTIME_OBJ"
else
    "$COMPILER" -emit obj -O0 -o "$runtime_dir/runtime-support.o" "$runtime_source" >/dev/null 2>&1
    clang -Wl,-dead_strip -o "$runtime_dir/program" "$runtime_dir/program.o" "$runtime_dir/runtime-support.o"
fi
set +e
"$runtime_dir/program"
runtime_status=$?
set -e
if [[ "$runtime_status" -ne 0 ]]; then
    printf 'dogfood failed: executable arena admission suite failed (exit %s)\n' "$runtime_status" >&2
    exit 1
fi
printf 'dogfood arena_runtime: malformed arenas/resource places rejected and valid DAG sharing accepted\n'

# Exercise the Elisa-native proof-state action layer itself. This is intentionally an
# executable harness rather than a report-only probe: both branches of split/cases must solve,
# rewrite requires an explicit equality, and a rejected action must leave the state unsolved.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/tactic-runtime.o" "$ROOT_DIR/examples/tactic_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    clang -Wl,-dead_strip -o "$runtime_dir/tactic-runtime" "$runtime_dir/tactic-runtime.o" "$RUNTIME_OBJ"
else
    clang -Wl,-dead_strip -o "$runtime_dir/tactic-runtime" "$runtime_dir/tactic-runtime.o"
fi
set +e
"$runtime_dir/tactic-runtime"
tactic_status=$?
set -e
if [[ "$tactic_status" -ne 0 ]]; then
    printf 'dogfood failed: executable tactic action suite failed (exit %s)\n' "$tactic_status" >&2
    exit 1
fi
printf 'dogfood tactic_runtime: kernel-backed state actions and branch obligations passed\n'

# Portable proof scripts are parsed and executed by the Elisa implementation itself. The
# script's source fingerprint is optional for reusable theorem states, but when present a stale
# script must fail even if its proposition is independently true.
portable_output="$REPORT_DIR/tactic-script.json"
portable_repeat_output="$REPORT_DIR/tactic-script.repeat.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script.json" "$ROOT_DIR/examples/verified.elisa" >"$portable_output"
portable_status=$?
set -e
if [[ "$portable_status" -ne 0 ]]; then
    printf 'dogfood failed: portable tactic script was not admitted (exit %s)\n' "$portable_status" >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script.json" "$ROOT_DIR/examples/verified.elisa" >"$portable_repeat_output"
portable_repeat_status=$?
set -e
if [[ "$portable_repeat_status" -ne 0 ]] || ! cmp -s "$portable_output" "$portable_repeat_output"; then
    printf 'dogfood failed: portable tactic script was non-deterministic\n' >&2
    exit 1
fi
python3 - "$portable_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
tactic = report["tactic"]
assert report["format"] == "elisa-proof-tactic-result-v1"
assert report["status"] == "proved"
assert report["source"]["status"] == "proved"
assert tactic["valid"] is True
assert tactic["solved"] is True
assert tactic["trace_replayed"] is True
assert tactic["kernel_trace_replayed"] is True
assert tactic["kernel_replayed"] is True
assert tactic["certificate_replayed"] is True
assert tactic["action_count"] == 2
assert len(report["state"]["trace"]) == 2
print("dogfood tactic_script: portable JSON trace and certificate passed")
PY
branch_output="$REPORT_DIR/tactic-script-branch.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_branch.json" "$ROOT_DIR/examples/verified.elisa" >"$branch_output"
branch_status=$?
set -e
if [[ "$branch_status" -ne 0 ]]; then
    printf 'dogfood failed: portable branch tactic script was not admitted (exit %s)\n' "$branch_status" >&2
    exit 1
fi
python3 - "$branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
tactic = report["tactic"]
assert report["status"] == "proved"
assert tactic["branch_present"] is True
assert tactic["branch_certificate_replayed"] is True
assert tactic["trace_replayed"] is True
assert tactic["kernel_trace_replayed"] is True
assert tactic["kernel_replayed"] is True
assert tactic["certificate_replayed"] is True
assert report["state"]["trace"][-1]["action"] == "split"
assert report["branches"]["left"]["solved"] is True
assert report["branches"]["right"]["solved"] is True
assert len(report["branches"]["left"]["trace"]) == 1
assert len(report["branches"]["right"]["trace"]) == 1
print("dogfood tactic_script_branch: both serialized child certificates replayed")
PY
nested_branch_output="$REPORT_DIR/tactic-script-nested-branch.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_branch.json" "$ROOT_DIR/examples/verified.elisa" >"$nested_branch_output"
nested_branch_status=$?
set -e
if [[ "$nested_branch_status" -ne 0 ]]; then
    printf 'dogfood failed: nested portable branch tactic script was not admitted (exit %s)\n' "$nested_branch_status" >&2
    exit 1
fi
python3 - "$nested_branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
tactic = report["tactic"]
assert report["status"] == "proved"
assert tactic["branch_present"] is True
assert tactic["branch_certificate_replayed"] is True
assert tactic["certificate_replayed"] is True
nested = report["branches"]["left"]
assert nested["branches"]["left"]["solved"] is True
assert nested["branches"]["right"]["solved"] is True
assert report["branches"]["right"]["solved"] is True
print("dogfood tactic_script_nested_branch: recursively replayed branch tree passed")
PY
nested_cases_output="$REPORT_DIR/tactic-script-nested-cases.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_nested_cases.json" "$ROOT_DIR/examples/verified.elisa" >"$nested_cases_output"
nested_cases_status=$?
set -e
if [[ "$nested_cases_status" -ne 0 ]]; then
    printf 'dogfood failed: nested portable cases tactic script was not admitted (exit %s)\n' "$nested_cases_status" >&2
    exit 1
fi
python3 - "$nested_cases_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["tactic"]["branch_certificate_replayed"] is True
nested = report["branches"]["left"]
assert nested["trace"][-1]["action"] == "cases"
assert nested["branches"]["left"]["facts"] == [{"kind": "bool", "value": True}]
assert nested["branches"]["right"]["facts"] == [{"kind": "bool", "value": True}]
print("dogfood tactic_script_nested_cases: recursive disjunction context replay passed")
PY
source_nested_branch_output="$REPORT_DIR/tactic-script-target-nested-branch.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target_nested_branch.json" "$ROOT_DIR/examples/verified_branch.elisa" >"$source_nested_branch_output"
source_nested_branch_status=$?
set -e
if [[ "$source_nested_branch_status" -ne 0 ]]; then
    printf 'dogfood failed: source-bound nested branch tactic script was not admitted (exit %s)\n' "$source_nested_branch_status" >&2
    exit 1
fi
python3 - "$source_nested_branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["source_goal_binding"] == {"bound": True, "goal_id": 1}
assert report["tactic"]["certificate_replayed"] is True
assert report["branches"]["left"]["branches"]["right"]["solved"] is True
print("dogfood tactic_script_target_nested_branch: source-bound tree certificate passed")
PY
incomplete_branch_output="$REPORT_DIR/tactic-script-branch-incomplete.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_branch_incomplete.json" "$ROOT_DIR/examples/verified.elisa" >"$incomplete_branch_output"
incomplete_branch_status=$?
set -e
if [[ "$incomplete_branch_status" -ne 1 ]]; then
    printf 'dogfood failed: incomplete portable branch tactic script was accepted (exit %s)\n' "$incomplete_branch_status" >&2
    exit 1
fi
python3 - "$incomplete_branch_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["tactic"]["branch_present"] is True
assert report["tactic"]["branch_certificate_replayed"] is False
assert report["tactic"]["certificate_replayed"] is False
assert report["branches"]["left"]["solved"] is True
assert report["branches"]["right"]["solved"] is False
print("dogfood tactic_script_branch_incomplete: an open child blocked admission")
PY
target_output="$REPORT_DIR/tactic-script-target.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target.json" "$ROOT_DIR/examples/verified.elisa" >"$target_output"
target_status=$?
set -e
if [[ "$target_status" -ne 0 ]]; then
    printf 'dogfood failed: source-bound tactic script was not admitted (exit %s)\n' "$target_status" >&2
    exit 1
fi
python3 - "$target_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
binding = report["source_goal_binding"]
assert report["status"] == "proved"
assert binding == {"bound": True, "goal_id": 7}
assert report["tactic"]["status"] == "proved"
assert report["tactic"]["certificate_replayed"] is True
assert len(report["state"]["initial_facts"]) == 1
assert report["state"]["initial_goal"] == report["state"]["goal"]
print("dogfood tactic_script_target: imported goal and facts were bound before replay")
PY
forged_target_output="$REPORT_DIR/tactic-script-target-forged.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_target_forged.json" "$ROOT_DIR/examples/verified.elisa" >"$forged_target_output"
forged_target_status=$?
set -e
if [[ "$forged_target_status" -ne 1 ]]; then
    printf 'dogfood failed: source-bound tactic script accepted a forged initial state (exit %s)\n' "$forged_target_status" >&2
    exit 1
fi
python3 - "$forged_target_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source_goal_binding"] == {"bound": True, "goal_id": 7}
assert report["tactic"]["valid"] is False
assert report["state"]["initial_goal"] == {"kind": "invalid"}
assert "source-bound" in report["tactic"]["reason"]
print("dogfood tactic_script_target_forged: imported state could not be replaced")
PY
stale_output="$REPORT_DIR/tactic-script-stale.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_stale.json" "$ROOT_DIR/examples/verified.elisa" >"$stale_output"
stale_status=$?
set -e
if [[ "$stale_status" -ne 1 ]]; then
    printf 'dogfood failed: stale portable tactic script was accepted (exit %s)\n' "$stale_status" >&2
    exit 1
fi
python3 - "$stale_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["fingerprint_match"] is False
assert report["tactic"]["certificate_replayed"] is True
assert "source_fingerprint" in report["tactic"]["reason"]
print("dogfood tactic_script_stale: source binding rejected stale certificate")
PY

if [[ "${ELISA_DOGFOOD_FULL:-0}" == "1" ]]; then
    # The complete implementation is currently an audit target, not a self-trust exception:
    # unsupported compiler/proof-language boundaries are expected to keep this report failed.
    run_probe full_implementation src/main.elisa 1
fi

printf 'dogfood audit passed: formalized layers are replay-complete\n'
