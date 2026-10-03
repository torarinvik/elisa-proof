# shellcheck shell=bash
# Part 1 of scripts/dogfood.sh; sourced in order by it, never run alone.
COMPILER="${ELISA_COMPILER_BIN:-}"
# shellcheck source=scripts/compiler_provenance.sh
source "$ROOT_DIR/scripts/compiler_provenance.sh"
if [[ -z "$COMPILER" ]]; then
    # Prefer the current source checkout's freshness-guarded stage1 wrapper;
    # installed stage1 snapshots can lag compiler changes in the sibling checkout.
    COMPILER="$(elisa_default_stage1 "$ROOT_DIR" || true)"
    if [[ -z "$COMPILER" ]]; then
        COMPILER="$(elisa_default_stage0 "$ROOT_DIR" || true)"
    fi
    if [[ -z "$COMPILER" ]]; then
        COMPILER="$(command -v elisac 2>/dev/null || true)"
    fi
fi
if [[ -z "$COMPILER" ]]; then
    printf 'dogfood failed: set ELISA_COMPILER_BIN to an Elisa compiler\n' >&2
    exit 1
fi
# Later probes invoke the compiler from temporary working directories. Resolve
# relative paths now so a missing executable cannot masquerade as an expected
# compiler rejection in those probes.
if [[ "$COMPILER" != */* ]]; then
    COMPILER="$(command -v "$COMPILER" 2>/dev/null || true)"
fi
if [[ -z "$COMPILER" ]]; then
    printf 'dogfood failed: configured Elisa compiler could not be resolved\n' >&2
    exit 1
fi
if [[ "$COMPILER" != /* ]]; then
    compiler_dir="$(cd "$(dirname "$COMPILER")" && pwd -P)"
    COMPILER="$compiler_dir/$(basename "$COMPILER")"
fi
if [[ ! -x "$COMPILER" ]]; then
    printf 'dogfood failed: resolved Elisa compiler is not executable: %s\n' "$COMPILER" >&2
    exit 1
fi
if elisa_compiler_is_stage0 "$COMPILER"; then
    elisa_verify_stage0_provenance "$COMPILER" "$ROOT_DIR" || exit $?
fi

# The depth-limit importer regression deliberately uses a source accepted by the bootstrap
# compiler. Resolve and provenance-check that compiler once so the test cannot accidentally
# change its oracle to whichever stage is selected for the dogfood run.
BOOTSTRAP_COMPILER="${ELISA_BOOTSTRAP_COMPILER_BIN:-${ELISACORE_BIN:-}}"
if [[ -z "$BOOTSTRAP_COMPILER" ]]; then
    if elisa_compiler_is_stage0 "$COMPILER"; then
        BOOTSTRAP_COMPILER="$COMPILER"
    else
        BOOTSTRAP_COMPILER="$(elisa_default_stage0 "$ROOT_DIR" || true)"
    fi
fi
if [[ -n "$BOOTSTRAP_COMPILER" ]]; then
    elisa_verify_stage0_provenance "$BOOTSTRAP_COMPILER" "$ROOT_DIR" || exit $?
fi

# A stage1 wrapper emits objects that use the self-hosted runtime. Keep this in
# sync with build.sh so the executable dogfood harness exercises the same product
# configuration as the proof binary itself.
RUNTIME_OBJ="${ELISA_RUNTIME_OBJ:-}"
COMPILER_IS_STAGE1=0
if [[ -z "$RUNTIME_OBJ" ]]; then
    driver="$(grep -o '/[^\"]*/scripts/elisac_stage1\.sh' "$COMPILER" 2>/dev/null | head -1 || true)"
    if [[ -z "$driver" && "$(basename "$COMPILER")" == "elisac_stage1.sh" ]]; then
        driver="$COMPILER"
    fi
    if [[ -n "$driver" ]]; then
        COMPILER_IS_STAGE1=1
        candidate="${driver%/scripts/elisac_stage1.sh}/build/runtime/elisacore_runtime.o"
        [[ -f "$candidate" ]] && RUNTIME_OBJ="$candidate"
    fi
fi
if [[ "$(basename "$COMPILER")" == "elisac-stage1" ]]; then
    COMPILER_IS_STAGE1=1
fi
if [[ "$COMPILER_IS_STAGE1" -eq 1 && -z "$RUNTIME_OBJ" && -f "${HOME}/.elisac/elisacore_runtime.o" ]]; then
    RUNTIME_OBJ="${HOME}/.elisac/elisacore_runtime.o"
fi

# The portable checker links only the kernel and the package reader; build it with the same
# compiler, in the same call, so the self-audit packages below replay outside the tool that
# produced them.
ELISA_COMPILER_BIN="$COMPILER" ELISA_RUNTIME_OBJ="$RUNTIME_OBJ" ELISA_PROOF_PRODUCTS=all "$ROOT_DIR/scripts/build.sh"
# build.sh has just refreshed the snapshot; the executable harnesses below that
# include compiler sources must compile from the same pinned export.
# shellcheck source=scripts/compiler_snapshot.sh
source "$ROOT_DIR/scripts/compiler_snapshot.sh"

REPORT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/elisa-proof-dogfood.XXXXXX")"
PROBE_PREFETCH_PID=""
trap '[[ -n "$PROBE_PREFETCH_PID" ]] && kill "$PROBE_PREFETCH_PID" 2>/dev/null; rm -rf "$REPORT_DIR"' EXIT
# ELISA_PROOF_JOBS>1 runs both verifier runs of every literal run_probe line in parallel first;
# run_probe then reads those stored runs in its usual order (scripts/prefetch_probes.py).
PROBE_CACHE=""
if [[ "${ELISA_PROOF_JOBS:-1}" -gt 1 ]]; then
    PROBE_CACHE="$REPORT_DIR/probe-cache"
    mkdir -p "$PROBE_CACHE"
    python3 "$ROOT_DIR/scripts/prefetch_probes.py" "$ROOT_DIR/scripts/dogfood.sh" "$ROOT_DIR/build/elisa-proof" "$PROBE_CACHE" "$ROOT_DIR" "$ELISA_PROOF_JOBS" &
    PROBE_PREFETCH_PID=$!
fi
PROFILE_HOOKS_SOURCE="${ELISA_PROFILE_HOOKS_SOURCE:-$SNAPSHOT_COMPILER/test/parity/profile_hooks.c}"
PROFILE_HOOKS_OBJ="${ELISA_PROFILE_HOOKS_OBJ:-$REPORT_DIR/profile-hooks.o}"
if [[ ! -f "$PROFILE_HOOKS_SOURCE" ]]; then
    printf 'dogfood failed: profiler ABI hook source is missing: %s\n' "$PROFILE_HOOKS_SOURCE" >&2
    exit 1
fi
clang -c -O2 -o "$PROFILE_HOOKS_OBJ" "$PROFILE_HOOKS_SOURCE"

link_native() {
    local output="$1"
    shift
    elisa_link_native "$REPORT_DIR" "${ELISA_DEAD_STRIP_LINK[@]}" -o "$output" "$@" "$PROFILE_HOOKS_OBJ"
}

# One verifier run of run_probe (run 1, or run 2 for the determinism repeat) into `output`, read
# from the prefetch when it stored that run. Sets probe_status to the verifier's exit status.
probe_verifier_run() {
    local label="$1" source="$2" run="$3" output="$4" entry=""
    if [[ -n "$PROBE_CACHE" ]]; then
        entry="$PROBE_CACHE/$label.$run"
        while [[ -f "$PROBE_CACHE/$label.pending" && ! -f "$entry.rc" ]] && kill -0 "$PROBE_PREFETCH_PID" 2>/dev/null; do
            sleep 0.1  # poll-ok: local file from our own prefetcher
        done
    fi
    if [[ -n "$entry" && -f "$entry.rc" ]]; then
        cat "$entry.err" >&2
        cp "$entry.json" "$output"
        probe_status="$(<"$entry.rc")"
        set -e
        return 0
    fi
    set +e
    "$ROOT_DIR/build/elisa-proof" --json "$ROOT_DIR/$source" >"$output"
    probe_status=$?
    set -e
}

run_probe() {
    local label="$1"
    local source="$2"
    local expected_status="$3"
    local output="$REPORT_DIR/$label.json"
    local repeat_output="$REPORT_DIR/$label.repeat.json"
    probe_verifier_run "$label" "$source" 1 "$output"
    local actual_status="$probe_status"
    if [[ "$actual_status" -ne "$expected_status" ]]; then
        printf 'dogfood failed: %s exited %s (expected %s)\n' "$label" "$actual_status" "$expected_status" >&2
        return 1
    fi
    probe_verifier_run "$label" "$source" 2 "$repeat_output"
    local repeat_status="$probe_status"
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

# The bounds slices and the insertion helper (whose `index` is an unsigned local bound
# to its own typed symbol) prove and replay independently.
run_probe kernel_core src/proof/kernel_core.elisa 0
run_probe kernel_core_fixture examples/dogfood_kernel_core.elisa 0
run_probe source_context_scope examples/source_context_scope.elisa 0
python3 - "$REPORT_DIR/kernel_core.json" "$REPORT_DIR/kernel_core_fixture.json" <<'PY'
import json
import sys

for path, proven in zip(sys.argv[1:], (37, 50)):
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    assert report["status"] == "proved"
    assert report["summary"]["proven"] == proven
    assert report["summary"]["obligations"] == proven
    assert report["findings"] == []
PY
# The kernel's own audit, exported as a package, replays in the separate checker theorem by
# theorem: the package carries every replayed goal, and the checker trusts no fingerprint.
for label in kernel_core kernel_core_fixture; do
    source_path="src/proof/kernel_core.elisa"
    [[ "$label" == kernel_core_fixture ]] && source_path="examples/dogfood_kernel_core.elisa"
    "$ROOT_DIR/build/elisa-proof" --package "$ROOT_DIR/$source_path" >"$REPORT_DIR/$label.package.json"
    if ! "$ROOT_DIR/build/elisa-proof-replay" "$REPORT_DIR/$label.package.json" >"$REPORT_DIR/$label.replay.json"; then
        printf 'dogfood failed: %s package did not replay in the portable checker\n' "$label" >&2
        exit 1
    fi
done
python3 - "$REPORT_DIR" kernel_core kernel_core_fixture <<'PY'
import json
import sys

report_dir = sys.argv[1]
for label in sys.argv[2:]:
    report, package, result = (json.load(open(f"{report_dir}/{label}{suffix}", encoding="utf-8"))
                               for suffix in (".json", ".package.json", ".replay.json"))
    replayed = sum(1 for goal in report["goals"] if goal["proven"] and goal.get("replay_status") == "replayed")
    if not (result["status"] == "replayed" and result["trust"]["kernel"] == "checked"
            and len(result["theorems"]) == len(package["theorems"]) == replayed > 0
            and all(theorem["status"] == "replayed" for theorem in result["theorems"])):
        raise SystemExit(f"dogfood failed: {label} package replay disagrees with its report")
    print(f"dogfood {label}: {replayed} packaged theorems replay in the portable checker")
PY
python3 - "$REPORT_DIR/source_context_scope.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["semantic_errors"] == 0
assert report["summary"]["obligations"] > 0
assert report["summary"]["proven"] == report["summary"]["obligations"]
assert report["findings"] == []
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
assert report["replay"]["gaps"] == 0
PY
run_probe quantifier_hypothesis examples/quantifier_hypothesis.elisa 0
run_probe rejected_include_trailing examples/rejected_include_trailing.elisa 1
run_probe include_alias_diamond examples/include_alias_diamond.elisa 0
run_probe include_macro examples/include_macro.elisa 0
run_probe rejected_include_cycle examples/rejected_include_cycle_a.elisa 1
python3 - "$REPORT_DIR/rejected_include_cycle.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["verification_state"] == "unsupported"
assert any(finding["kind"] == "import-error" and finding["status"] == "unsupported" for finding in report["findings"])
assert report["replay"]["gaps"] == 0
PY

# Embedded NUL bytes must not be truncated at the proof importer's C-string file API.
# Before the guard, this source imported `included.elisa` and proved although the compiler
# rejected the actual filename containing the NUL suffix.
nul_include_dir="$REPORT_DIR/nul-include"
mkdir -p "$nul_include_dir"
python3 - "$nul_include_dir" <<'PY'
from pathlib import Path
import sys

directory = Path(sys.argv[1])
(directory / "included.elisa").write_text(
    "def nul_import_identity(x: i64) -> i64:\n"
    "    ensure result == x\n"
    "    return x\n",
    encoding="utf-8",
)
(directory / "entry.elisa").write_bytes(
    b'include "./included.elisa\x00ignored.elisa"\n'
    b'def use_nul_import(x: i64) -> i64:\n'
    b'    ensure result == x\n'
    b'    return nul_import_identity(x)\n'
)
PY
if "$COMPILER" -permissive -emit obj -O0 -o "$nul_include_dir/entry.o" "$nul_include_dir/entry.elisa" >"$nul_include_dir/compiler.log" 2>&1; then
    printf 'dogfood failed: compiler accepted an include path containing NUL\n' >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --json "$nul_include_dir/entry.elisa" >"$nul_include_dir/proof.json"
nul_include_status=$?
set -e
if [[ "$nul_include_status" -ne 1 ]]; then
    printf 'dogfood failed: proof importer returned %s for an include path containing NUL\n' "$nul_include_status" >&2
    exit 1
fi
python3 - "$nul_include_dir/proof.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["summary"]["semantic_errors"] == 0
assert any(finding["kind"] == "import-error" for finding in report["findings"])
declarations = {entry["name"] for entry in report["declaration_details"]}
assert declarations == set()
assert report["source"]["bytes"] == 0
assert report["replay"]["gaps"] == 0
print("dogfood include_nul: proof importer rejects the compiler-invalid path")
PY

# Root source has the same byte-length boundary as included files. The compiler tokenizes the
# complete buffer, so the proof assistant must not stop at an embedded NUL and certify only a
# valid prefix while ignoring a compiler-visible syntax error in the suffix.
nul_root_source="$REPORT_DIR/nul-root.elisa"
python3 - "$nul_root_source" <<'PY'
from pathlib import Path
import sys

Path(sys.argv[1]).write_bytes(
    b"def proof(x: i64) -> void:\n"
    b"    requires x >= 0\n"
    b"    assert x >= 0 by:\n"
    b"        assert x >= 0\n"
    b"\x00"
    b"def broken(:\n"
)
PY
if "$COMPILER" -permissive -emit obj -O0 -o "$REPORT_DIR/nul-root.o" "$nul_root_source" >"$REPORT_DIR/nul-root.compiler.log" 2>&1; then
    printf 'dogfood failed: compiler accepted the NUL-containing root-source regression\n' >&2
    exit 1
fi
set +e
"$ROOT_DIR/build/elisa-proof" --json "$nul_root_source" >"$REPORT_DIR/nul-root.json"
nul_root_status=$?
set -e
if [[ "$nul_root_status" -ne 1 ]]; then
    printf 'dogfood failed: proof assistant returned %s for compiler-invalid bytes after root-source NUL\n' "$nul_root_status" >&2
    exit 1
fi
python3 - "$REPORT_DIR/nul-root.json" "$nul_root_source" <<'PY'
import json
import sys
from pathlib import Path

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
source_bytes = Path(sys.argv[2]).read_bytes()
assert report["status"] == "failed"
assert report["summary"]["declarations"] == 0
assert report["summary"]["obligations"] == 0
assert report["summary"]["proven"] == 0
assert report["summary"]["failed"] > 0
assert report["summary"]["semantic_errors"] == 0
assert report["source"]["bytes"] == len(source_bytes)
assert any(finding["kind"] == "parse-error" for finding in report["findings"])
assert report["replay"]["gaps"] == 0
print("dogfood root_nul: proof parser consumes the compiler-visible full source extent")
PY

# A left-associated source expression is parsed iteratively but several semantic
# frontend passes recurse over its AST. The operator/type pass has a lower explicit
# recursion bound and must reject the unexamined suffix instead of exhausting the
# native stack. Stage0 accepts this source in permissive mode; proof import must fail
# closed with a valid, replay-gap-free report rather than crash.
if [[ -n "$BOOTSTRAP_COMPILER" ]]; then
python3 - "$BOOTSTRAP_COMPILER" "$ROOT_DIR/build/elisa-proof" "$REPORT_DIR/deep_expression.elisa" "$REPORT_DIR/deep_expression.o" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

compiler, proof, source_path, object_path = sys.argv[1:]
terms = 768
expression = " + ".join(["x"] * terms)
source = (
    "def deep_expression(x: i64) -> i64:\n"
    "    ensure result == x\n"
    f"    intermediate: i64 = {expression}\n"
    "    return x\n"
)
Path(source_path).write_text(source)
compiled = subprocess.run(
    [compiler, "-permissive", "-emit", "obj", "-O0", "-o", object_path, source_path],
    capture_output=True,
)
assert compiled.returncode == 0, compiled.stderr.decode("utf-8", errors="replace")
checked = subprocess.run([proof, "--json", source_path], capture_output=True, timeout=30)
assert checked.returncode == 1, (checked.returncode, checked.stdout[:500], checked.stderr[:500])
report = json.loads(checked.stdout)
assert report["status"] == "failed"
assert report["verification_state"] == "unsupported"
assert report["summary"]["semantic_errors"] == 1
assert report["summary"]["obligations"] == 0
assert any(
    "safe semantic-analysis limit" in item["message"]
    for item in report["semantic_diagnostics"]
)
assert any(item["kind"] == "semantic-analysis-depth" for item in report["findings"])
assert not any(item["kind"] == "resource-expression-depth" for item in report["findings"])
assert report["replay"]["gaps"] == 0
assert report["kernel"]["independent_replay"] is True
print("dogfood deep_expression: semantic depth exhaustion is rejected without a crash")
PY
else
    printf 'dogfood deep_expression: skipped (no provenance-verified Stage0 compiler is available)\n'
fi

# Elisa accepts legacy single-byte Latin-1 letters in identifiers as well as UTF-8 names. The
# report encoder must therefore escape malformed UTF-8 bytes without damaging valid multibyte
# text, so ordinary JSON clients can still parse every compiler-accepted report.
python3 - "$COMPILER" "$ROOT_DIR/build/elisa-proof" "$REPORT_DIR/latin1_identifier.elisa" "$REPORT_DIR/latin1_identifier.o" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

compiler, proof, source_path, object_path = sys.argv[1:]
# Keep the invalid single-byte identifier separate from the valid UTF-8 source bytes.
source = (
    b"def latin_\xff(x: i64) -> i64:\n"
    b"    ensure result == x\n"
    b"    return x\n"
    + "def lambda_λ(x: i64) -> i64:\n    ensure result == x\n    return x\n".encode("utf-8")
    + "def cjk_漢(x: i64) -> i64:\n    ensure result == x\n    return x\n".encode("utf-8")
    + (
        "def deseret_𐐀(x: i64) -> i64:\n    ensure result == x\n    return x\n"
        "def cjk_extension_b_𠀀(x: i64) -> i64:\n    ensure result == x\n    return x\n"
        "def mathematical_𝜆_and_𝟝(x: i64) -> i64:\n    ensure result == x\n    return x\n"
        "def adlam_digit_x𞥐(x: i64) -> i64:\n    ensure result == x\n    return x\n"
    ).encode("utf-8")
)
Path(source_path).write_bytes(source)
compiled = subprocess.run(
    [compiler, "-permissive", "-emit", "obj", "-O0", "-o", object_path, source_path],
    capture_output=True,
)
assert compiled.returncode == 0, compiled.stderr.decode("utf-8", errors="replace")
checked = subprocess.run([proof, "--json", source_path], capture_output=True)
assert checked.returncode == 0, checked.stdout.decode("utf-8", errors="replace")
report = json.loads(checked.stdout)
assert report["status"] == "proved"
assert report["source"]["bytes"] == len(source)
verified = {
    item["name"]
    for item in report["declaration_details"]
    if item["kind"] == "function" and item["verified"]
}
assert {
    "latin_ÿ",
    "lambda_λ",
    "cjk_漢",
    "deseret_𐐀",
    "cjk_extension_b_𠀀",
    "mathematical_𝜆_and_𝟝",
    "adlam_digit_x𞥐",
} <= verified

# Semantic diagnostics are owned byte arrays and use the same encoder through
# proof_push_json_bytes; keep that path valid for a non-ASCII unresolved identifier too.
diagnostic_source_path = source_path.replace(".elisa", "-diagnostic.elisa")
diagnostic_object_path = object_path.replace(".o", "-diagnostic.o")
Path(diagnostic_source_path).write_bytes(b"def f() -> i64:\n    return missing_\xff\n")
rejected_compile = subprocess.run(
    [compiler, "-permissive", "-emit", "obj", "-O0", "-o", diagnostic_object_path, diagnostic_source_path],
    capture_output=True,
)
assert rejected_compile.returncode != 0
diagnostic_check = subprocess.run([proof, "--json", diagnostic_source_path], capture_output=True)
assert diagnostic_check.returncode == 1
diagnostic_report = json.loads(diagnostic_check.stdout)
assert diagnostic_report["status"] == "failed"
assert any("missing_ÿ" in item["message"] for item in diagnostic_report["semantic_diagnostics"])
print("dogfood json_latin1: invalid byte escaped and valid UTF-8 preserved in reports and diagnostics")
PY

# Absolute include paths are valid in the compiler and must not be rebased against the
# including file's directory by the proof importer.
absolute_include_dir="$REPORT_DIR/absolute-include"
mkdir -p "$absolute_include_dir"
absolute_include_library="$absolute_include_dir/library.elisa"
absolute_include_entry="$absolute_include_dir/entry.elisa"
printf 'def absolute_include_value() -> i64:\n    ensure result == 42\n    return 42\n' >"$absolute_include_library"
printf 'include "%s"\ndef absolute_include_entry() -> i64:\n    ensure result == 42\n    return 42\n' "$absolute_include_library" >"$absolute_include_entry"
"$COMPILER" -emit obj -O0 -o "$absolute_include_dir/entry.o" "$absolute_include_entry" >/dev/null 2>&1
"$ROOT_DIR/build/elisa-proof" --json "$absolute_include_entry" >"$REPORT_DIR/include_absolute.json"
python3 - "$REPORT_DIR/include_absolute.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
names = {entry["name"] for entry in report["declaration_details"]}
assert {"absolute_include_value", "absolute_include_entry"} <= names
print("dogfood include_absolute: compiler and proof importer resolved the same file")
PY
working_directory_dir="$REPORT_DIR/working-directory"
physical_working_dir="$working_directory_dir/physical"
logical_working_dir="$working_directory_dir/logical"
stale_working_dir="$working_directory_dir/stale"
mkdir -p "$physical_working_dir" "$stale_working_dir"
ln -s "$physical_working_dir" "$logical_working_dir"
printf 'def shared_include_value() -> i64:\n    return 42\n' >"$physical_working_dir/library.elisa"
printf 'def shared_include_value() -> i64:\n    return 0\n' >"$stale_working_dir/library.elisa"
printf 'include "./library.elisa"\ninclude "%s/library.elisa"\ndef imported_entry() -> i64:\n    ensure result == 42\n    return 42\n' "$physical_working_dir" >"$physical_working_dir/duplicate_entry.elisa"
printf 'include "./library.elisa"\ndef imported_entry() -> i64:\n    ensure result == 42\n    return 42\n' >"$physical_working_dir/stale_pwd_entry.elisa"
(
    cd -L "$logical_working_dir"
    if "$COMPILER" -emit obj -O0 -o "$working_directory_dir/duplicate.o" duplicate_entry.elisa >/dev/null 2>&1; then
        printf 'dogfood failed: compiler accepted duplicate includes through distinct symlink paths\n' >&2
        exit 1
    fi
    if "$ROOT_DIR/build/elisa-proof" --json duplicate_entry.elisa >"$REPORT_DIR/include_symlink_cwd.json"; then
        printf 'dogfood failed: proof importer merged paths that compiler keeps distinct\n' >&2
        exit 1
    fi
)
python3 - "$REPORT_DIR/include_symlink_cwd.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["summary"]["semantic_errors"] > 0
assert report["replay"]["gaps"] == 0
print("dogfood include_symlink_cwd: lexical include identity matches compiler cwd")
PY
(
    cd "$physical_working_dir"
    PWD="$stale_working_dir" "$COMPILER" -emit obj -O0 -o "$working_directory_dir/stale-pwd.o" stale_pwd_entry.elisa >/dev/null 2>&1
    PWD="$stale_working_dir" "$ROOT_DIR/build/elisa-proof" --json stale_pwd_entry.elisa >"$REPORT_DIR/include_stale_pwd.json"
)
python3 - "$REPORT_DIR/include_stale_pwd.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
print("dogfood include_stale_pwd: compiler and prover ignore stale PWD metadata")
PY
