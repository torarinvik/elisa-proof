# shellcheck shell=bash
# Part 7 of scripts/dogfood.sh; sourced in order by it, never run alone.
printf 'dogfood proposition_admission_runtime: abstract atoms, typed source terms, and tactic boundaries passed\n'

"$COMPILER" -emit obj -O0 -o "$runtime_dir/comparison-runtime.o" "$ROOT_DIR/examples/kernel_comparison_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/comparison-runtime" "$runtime_dir/comparison-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/comparison-runtime" "$runtime_dir/comparison-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/comparison-runtime"
printf 'dogfood comparison_runtime: witnessed comparisons, typed negative constants, width-tagged unsigned literals, and every range-quantifier instance checked; unwitnessed reflexivity refused\n'

# Congruence closure is exercised against the kernel directly: every participating former must
# carry an equality, and every excluded former (call, move, address-of, namespace path, guarded
# access, quantifier) must refuse to, on both the dedicated rule and full goal replay.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/congruence-runtime.o" "$ROOT_DIR/examples/kernel_congruence_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/congruence-runtime" "$runtime_dir/congruence-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/congruence-runtime" "$runtime_dir/congruence-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/congruence-runtime"
printf 'dogfood congruence_runtime: participating formers carried equalities and excluded formers refused\n'

# Propositional fact projection is exercised against the kernel directly: a conjunction entails
# each conjunct, a negated disjunction entails each negated disjunct, a double negation cancels,
# and the dual forms - a disjunction, a negated conjunction - must stay refused in both signs.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/projection-runtime.o" "$ROOT_DIR/examples/kernel_projection_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/projection-runtime" "$runtime_dir/projection-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/projection-runtime" "$runtime_dir/projection-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/projection-runtime"
printf 'dogfood projection_runtime: conjunct and negated-disjunct projection admitted, duals refused\n'

# Declared effect containment is checked against the kernel directly: contained rows admitted,
# uncontained rows refused, and every malformed effect graph rejected rather than interpreted.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/effect-runtime.o" "$ROOT_DIR/examples/kernel_effect_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/effect-runtime" "$runtime_dir/effect-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/effect-runtime" "$runtime_dir/effect-runtime.o" "$runtime_dir/runtime-support.o"
fi
"$runtime_dir/effect-runtime"
printf 'dogfood effect_runtime: contained rows admitted and uncontained or malformed rows refused\n'

# Bootstrap coverage: compile the runtime with stage0 as well; an installed stage1
# runtime is not an implicit bootstrap dependency. The reduced resource trace
# guards the stage0 miscompile of allocations made through an unannotated mutable
# reference inside a region-polymorphic function (see AUDIT.md); the full arena
# harness then confirms the whole replay layer under the bootstrap compiler.
# Respect the same explicit stage0 compiler supplied to the stage1 driver/build; otherwise a
# stale, unrelated `elisac-stage0` earlier on PATH can replace the verified bootstrap product.
if [[ -n "$BOOTSTRAP_COMPILER" ]]; then
    compile_bootstrap_object() {
        local source="$1"
        local output="$2"
        local log="${output%.o}.compile.log"
        if ! "$BOOTSTRAP_COMPILER" -emit obj -O0 -o "$output" "$source" >"$log" 2>&1; then
            printf 'dogfood failed: stage0 compiler rejected %s; diagnostics follow:\n' "$source" >&2
            cat "$log" >&2
            return 1
        fi
    }

    if ! compile_bootstrap_object "$runtime_source" "$runtime_dir/bootstrap-runtime.o"; then
        exit 1
    fi
    # The raw runtime support object intentionally leaves the optional profiler
    # ABI unresolved.  Keep the stage0 bootstrap link honest by supplying the
    # same small hook implementation used by the compiler parity harness.
    for bootstrap_example in kernel_comparison_runtime kernel_congruence_runtime kernel_projection_runtime kernel_effect_runtime kernel_resource_bootstrap_runtime kernel_arena_runtime kernel_proposition_admission_runtime; do
        if ! compile_bootstrap_object "$ROOT_DIR/examples/$bootstrap_example.elisa" "$runtime_dir/bootstrap-$bootstrap_example.o"; then
            exit 1
        fi
        link_native "$runtime_dir/bootstrap-$bootstrap_example" "$runtime_dir/bootstrap-$bootstrap_example.o" "$runtime_dir/bootstrap-runtime.o"
        set +e
        "$runtime_dir/bootstrap-$bootstrap_example"
        bootstrap_status=$?
        set -e
        if [[ "$bootstrap_status" -ne 0 ]]; then
            printf 'dogfood failed: stage0-built %s exited %s\n' "$bootstrap_example" "$bootstrap_status" >&2
            exit 1
        fi
        printf 'dogfood bootstrap_%s: stage0 harness passed\n' "$bootstrap_example"
    done
else
    printf 'dogfood bootstrap: skipped (elisac-stage0 unavailable)\n'
fi

# Exercise the Elisa-native proof-state action layer itself. This is intentionally an
# executable harness rather than a report-only probe: both branches of split/cases must solve,
# rewrite requires an explicit equality, and a rejected action must leave the state unsolved.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/tactic-runtime.o" "$SNAPSHOT_ROOT/examples/tactic_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/tactic-runtime" "$runtime_dir/tactic-runtime.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/tactic-runtime" "$runtime_dir/tactic-runtime.o"
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
# Required-reference provenance must reject altered declarations, not merely replay a null test.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/required-reference-replay.o" "$SNAPSHOT_ROOT/examples/required_reference_replay_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/required-reference-replay" "$runtime_dir/required-reference-replay.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/required-reference-replay" "$runtime_dir/required-reference-replay.o"
fi
"$runtime_dir/required-reference-replay"
printf 'dogfood required_reference_replay: nullable, value, missing, shifted, duplicate and alias-collision origins rejected\n'


# Corrupt a checked lemma-summary binding in memory and require independent replay to reject every
# caller certificate that tries to consume the now-mismatched instantiated postcondition.
"$COMPILER" -emit obj -O0 -o "$runtime_dir/lemma-summary-replay.o" "$SNAPSHOT_ROOT/examples/lemma_summary_replay_runtime.elisa" >/dev/null 2>&1
if [[ -n "$RUNTIME_OBJ" ]]; then
    link_native "$runtime_dir/lemma-summary-replay" "$runtime_dir/lemma-summary-replay.o" "$RUNTIME_OBJ"
else
    link_native "$runtime_dir/lemma-summary-replay" "$runtime_dir/lemma-summary-replay.o"
fi
set +e
"$runtime_dir/lemma-summary-replay"
lemma_summary_replay_status=$?
set -e
if [[ "$lemma_summary_replay_status" -ne 0 ]]; then
    printf 'dogfood failed: forged lemma summary survived replay (exit %s)\n' "$lemma_summary_replay_status" >&2
    exit 1
fi
printf 'dogfood summary_replay: mismatched lemma/function instantiations and AST/kernel drift rejected\n'

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
quantifier_output="$REPORT_DIR/tactic-script-quantifier.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_quantifier.json" "$ROOT_DIR/examples/verified.elisa" >"$quantifier_output"
quantifier_status=$?
set -e
if [[ "$quantifier_status" -ne 0 ]]; then
    printf 'dogfood failed: portable quantifier tactic was not admitted (exit %s)\n' "$quantifier_status" >&2
    exit 1
fi
python3 - "$quantifier_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
tactic = report["tactic"]
assert report["status"] == "proved"
assert tactic["valid"] is True
assert tactic["solved"] is True
assert tactic["kernel_trace_replayed"] is True
assert tactic["kernel_replayed"] is True
assert tactic["certificate_replayed"] is True
print("dogfood tactic_script_quantifier: producer and kernel agreed on finite quantifier replay")
PY
for rejected_line_fixture in tactic_script_rejected_large_line tactic_script_rejected_large_expr_line; do
    rejected_line_output="$REPORT_DIR/$rejected_line_fixture.json"
    set +e
    "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/$rejected_line_fixture.json" "$ROOT_DIR/examples/verified.elisa" >"$rejected_line_output"
    rejected_line_status=$?
    set -e
    if [[ "$rejected_line_status" -ne 1 ]]; then
        printf 'dogfood failed: overflowing JSON line was accepted for %s\n' "$rejected_line_fixture" >&2
        exit 1
    fi
    python3 - "$rejected_line_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["tactic"]["valid"] is False
assert report["tactic"]["action_count"] == 0
PY
done
printf 'dogfood tactic_json_lines: overflowing source and expression lines were rejected\n'
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
binding = report["source_goal_binding"]
assert binding["bound"] and binding["goal_id"] == 1 and binding["previously_proven"]
assert binding["fingerprint_match"] is True
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
assert binding["bound"] and binding["goal_id"] == 7 and binding["previously_proven"]
assert binding["fingerprint_match"] is True
assert report["tactic"]["status"] == "proved"
assert report["tactic"]["certificate_replayed"] is True
assert len(report["state"]["initial_facts"]) == 3
assert any(
    fact["kind"] == "call" and fact["callee"]["name"] == "__elisa_primitive_scalar_type"
    for fact in report["state"]["initial_facts"]
)
assert any(
    fact["kind"] == "call" and fact["callee"]["name"] == "__elisa_signed_type_bound"
    for fact in report["state"]["initial_facts"]
)
assert report["state"]["initial_goal"] == report["state"]["goal"]
print("dogfood tactic_script_target: imported goal and facts were bound before replay")
PY
repair_target_output="$REPORT_DIR/tactic-script-repair-target.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_repair_target.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" >"$repair_target_output"
repair_target_status=$?
set -e
if [[ "$repair_target_status" -ne 0 ]]; then
    printf 'dogfood failed: source-bound tactic did not repair an open goal (exit %s)\n' "$repair_target_status" >&2
    exit 1
fi
python3 - "$repair_target_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["admission_scope"] == "target"
assert report["source"]["status"] == "failed"
assert report["source"]["complete"] is False
assert report["source"]["admissible"] is True
binding = report["source_goal_binding"]
assert binding["bound"] and binding["goal_id"] == 1 and not binding["previously_proven"]
assert binding["goal_fingerprint"]["value"] == 2903951783
assert binding["fingerprint_match"] is True
assert report["tactic"]["certificate_replayed"] is True
assert [step["action"] for step in report["state"]["trace"]] == ["rewrite", "decide"]
print("dogfood tactic_script_repair_target: an open imported goal was independently repaired")
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
binding = report["source_goal_binding"]
assert binding["bound"] and binding["goal_id"] == 7 and binding["previously_proven"]
assert report["tactic"]["valid"] is False
assert report["state"]["initial_goal"] == {"kind": "invalid"}
assert "source-bound" in report["tactic"]["reason"]
print("dogfood tactic_script_target_forged: imported state could not be replaced")
PY
forged_quantifier_output="$REPORT_DIR/tactic-script-source-bound-forged-quantifier.json"
set +e
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_source_bound_forged_quantifier.json" "$ROOT_DIR/examples/rejected_source_bound_exists.elisa" >"$forged_quantifier_output"
forged_quantifier_status=$?
set -e
if [[ "$forged_quantifier_status" -ne 1 ]]; then
    printf 'dogfood failed: source-bound tactic weakened a universal quantifier (exit %s)\n' "$forged_quantifier_status" >&2
    exit 1
fi
python3 - "$forged_quantifier_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["status"] == "failed"
assert report["source"]["admissible"] is True
assert report["tactic"]["valid"] is False
assert report["tactic"]["solved"] is False
assert report["state"]["action_count"] == 1
assert report["state"]["trace"][0]["accepted"] is False
assert report["state"]["initial_goal"]["kind"] == "block"
print("dogfood tactic_script_source_bound_forged_quantifier: compiler quantifier kind remained authoritative")
PY
forged_instantiation_output="$REPORT_DIR/forged-instantiation.json"
if "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_source_bound_forged_instantiation.json" "$ROOT_DIR/examples/source_bound_exists.elisa" >"$forged_instantiation_output"; then
    printf 'dogfood failed: existential source hypothesis admitted universal instantiation\n' >&2
    exit 1
fi
python3 - "$forged_instantiation_output" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["admissible"] is True
assert report["tactic"]["certificate_replayed"] is False
assert report["state"]["initial_facts"][0]["kind"] == "block"
assert report["state"]["trace"][0]["action"] == "instantiate"
assert report["state"]["trace"][0]["accepted"] is False
print("dogfood forged_instantiation: existential hypothesis cannot be relabeled universal")
PY
exact_integer_output="$REPORT_DIR/tactic-integer-exact.json"
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_integer_rounding.json" "$ROOT_DIR/examples/tactic_integer_exact_boundary.elisa" >"$exact_integer_output"
python3 - "$exact_integer_output" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "proved"
assert report["tactic"]["certificate_replayed"] is True
assert report["state"]["initial_goal"]["left"]["value"] == 9007199254740991
PY
rounding_output="$REPORT_DIR/tactic-integer-rounding.json"
if "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_integer_rounding.json" "$ROOT_DIR/examples/rejected_tactic_integer_rounding.elisa" >"$rounding_output"; then
    printf 'dogfood failed: rounded integers admitted a false source equality\n' >&2
    exit 1
fi
python3 - "$rounding_output" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "failed"
assert report["source"]["admissible"] is True
assert report["source_goal_binding"]["previously_proven"] is False
assert report["tactic"]["valid"] is False
assert report["tactic"]["certificate_replayed"] is False
print("dogfood integer_rounding: lossy JSON numbers cannot prove a different source goal")
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
    # The complete implementation is currently an audit target, not a self-trust exception.
    # Keep this path bounded: a resource stop is an explicit incomplete audit (exit 3), not a
    # proof failure and not a reason to let an exploratory dogfood run consume the host.
    full_audit_output="$REPORT_DIR/full-implementation-audit.json"
    set +e
    "$ROOT_DIR/scripts/audit_full_source.sh" >"$full_audit_output"
    full_audit_status=$?
    set -e
    if [[ "$full_audit_status" -eq 3 ]]; then
        printf 'dogfood full_implementation: bounded audit incomplete (see %s)\n' "$full_audit_output" >&2
        exit 3
    fi
    if [[ "$full_audit_status" -ne 0 ]]; then
        printf 'dogfood full_implementation: audit harness failed (exit %s)\n' "$full_audit_status" >&2
        exit 1
    fi
    python3 - "$full_audit_output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    audit = json.load(handle)
if not audit["complete"] or audit["replay_gaps"] != 0:
    raise SystemExit("dogfood failed: completed full-source audit did not have zero replay gaps")
print(
    "dogfood full_implementation: completed with "
    f"report_status={audit['report_status']} verification_state={audit['report_verification_state']} "
    f"obligations={audit.get('obligations')} proven={audit.get('proven')}"
)
PY
fi

printf 'dogfood audit passed: formalized layers are replay-complete\n'
