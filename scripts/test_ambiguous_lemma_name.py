"""Two lemmas with one name must fail closed without crashing the checker."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("ambiguous-lemma checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]

BINARY = Path(qualified_test_binary.proof_test_binary(ROOT))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/rejected_ambiguous_lemma_name.elisa")],
                     capture_output=True, text=True, timeout=120)
# Exit 1 is a verdict; a signal (negative) or trap status is the regression this guards.
assert run.returncode == 1, (run.returncode, run.stderr[-2000:])
report = json.loads(run.stdout)
assert report["status"] == "failed", report["status"]
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
ambiguous = [f for f in report["findings"] if f["kind"] == "lemma-ambiguous"]
assert len(ambiguous) == 2, report["findings"]
details = [d for d in report["declaration_details"] if d["name"] == "shared_bound"]
assert len(details) == 2 and all(
    d["kind"] == "lemma" and not d["verified"]
    and d["verification_reason"] == "ambiguous-lemma-name"
    for d in details
), details
assert report["trust"]["trusted_assumptions"] == [], report["trust"]
ambiguous_status = [f for f in report["functions"] if f["name"] == "shared_bound"]
assert len(ambiguous_status) == 1 and not ambiguous_status[0]["proved"]
assert ambiguous_status[0]["goals"] == ambiguous_status[0]["open_goals"] == 0
assert ambiguous_status[0]["findings"] == 2, ambiguous_status
use = next(d for d in report["declaration_details"] if d["name"] == "use_ambiguous_lemma")
assert not use["verified"], use
caller_traces = [t for t in report["kernel"]["fact_traces"]
                 if t["name"] == "use_ambiguous_lemma"]
assert caller_traces and not any(t["kind"] in ("function-summary", "lemma-summary")
                                 for t in caller_traces), caller_traces

# A unique lemma name still resolves and replays; the fail-closed rule is not a blanket
# rejection of lemma summaries.
positive = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/lemma.elisa")],
                          capture_output=True, text=True, timeout=120)
assert positive.returncode == 0, (positive.returncode, positive.stderr, positive.stdout)
positive_report = json.loads(positive.stdout)
assert positive_report["status"] == positive_report["verification_state"] == "proved"
assert positive_report["summary"]["semantic_errors"] == 0
assert positive_report["replay"]["gaps"] == 0
assert positive_report["replay"]["certificates"] == positive_report["replay"]["replayed"]
assert positive_report["trust"]["trusted_assumptions"] == []
assert any(d["name"] == "nonnegative" and d["kind"] == "lemma" and d["verified"]
           for d in positive_report["declaration_details"]), positive_report["declaration_details"]

# Duplicate executable names remain executable and correctly aligned; their status entries are
# positive evidence that the lemma-specific fail-closed case does not apply to ordinary functions.
executables = subprocess.run([str(BINARY), "--json",
    str(ROOT / "examples/ambiguous_name_purity_probe.elisa")],
    capture_output=True, text=True, timeout=120)
assert executables.returncode == 0, (executables.returncode, executables.stderr, executables.stdout)
executable_report = json.loads(executables.stdout)
assert executable_report["status"] == executable_report["verification_state"] == "proved"
assert executable_report["summary"]["semantic_errors"] == 0
assert executable_report["replay"]["gaps"] == 0
assert executable_report["replay"]["certificates"] == executable_report["replay"]["replayed"]
assert executable_report["trust"]["trusted_assumptions"] == []
shared_declarations = [d for d in executable_report["declaration_details"]
                       if d["name"] == "shared"]
assert len(shared_declarations) == 2 and all(
    d["kind"] == "function" and d["verified"] for d in shared_declarations
), shared_declarations
assert any(f["name"] == "shared" and f["proved"]
           for f in executable_report["functions"]), executable_report["functions"]

# A function and a lemma may share a leaf name across modules. Their source owners remain
# distinct: the unrelated function's failed postcondition must not enter the lemma's proof-goal
# list or turn the otherwise valid theorem into a source/replay gap.
cross_kind = subprocess.run([str(BINARY), "--json",
    str(ROOT / "examples/cross_module_lemma_function_name.elisa")],
    capture_output=True, text=True, timeout=120)
assert cross_kind.returncode == 1, (cross_kind.returncode, cross_kind.stderr[-2000:])
cross_kind_report = json.loads(cross_kind.stdout)
assert cross_kind_report["status"] == "failed", cross_kind_report["status"]
same_name_rows = [d for d in cross_kind_report["declaration_details"]
                  if d["name"] == "shared_owner"]
lemma_rows = [d for d in same_name_rows if d["kind"] == "lemma"]
function_rows = [d for d in same_name_rows if d["kind"] == "function"]
assert len(lemma_rows) == 1 and lemma_rows[0]["verified"], same_name_rows
assert len(function_rows) == 1 and not function_rows[0]["verified"], same_name_rows
theorem_rows = [t for t in cross_kind_report["theorems"] if t["name"] == "shared_owner"]
assert len(theorem_rows) == 1, theorem_rows
theorem = theorem_rows[0]
assert theorem["verified"] and theorem["source_claim_admissible"] and theorem["proof_goals_valid"], theorem
goals_by_id = {goal["goal_id"]: goal for goal in cross_kind_report["goals"]}
theorem_goals = [goals_by_id[goal["goal_id"]] for goal in theorem["proof_goals"]]
assert theorem_goals and all(goal["line"] == theorem["line"] and goal["proven"]
                             for goal in theorem_goals), (theorem, theorem_goals)
failed_sibling_goals = [goal for goal in cross_kind_report["goals"]
                        if goal["name"] == "shared_owner" and not goal["proven"]]
assert failed_sibling_goals and all(goal["line"] != theorem["line"]
                                    for goal in failed_sibling_goals), failed_sibling_goals
print("ambiguous lemmas fail closed; unique lemmas and duplicate executable names remain verified")
