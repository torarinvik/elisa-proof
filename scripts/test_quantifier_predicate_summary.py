"""Bounded quantifier predicates use source-replayed callee equations, not axioms."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def run(fixture):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=90)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    return result.returncode, report


code, positive = run("quantifier_predicate_summary.elisa")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0
for target in ("quantified_summary", "quantified_inclusive_summary", "quantified_default_summary",
               "quantified_conjunction_summary", "quantified_existential_summary",
               "signed_quantified_witness", "signed_quantified_all"):
    goals = [g for g in positive["goals"] if g["name"] == target and g["proven"]]
    assert any(any(origin and origin["kind"] == "function-summary"
                   for origin in goal["fact_origins"]) for goal in goals), target

code, negative = run("rejected_quantifier_predicate_summary.elisa")
assert code == 1 and negative["status"] == "failed", negative["findings"]
for target in ("rejected_false_summary", "rejected_missing_precondition", "rejected_negative_instance",
               "rejected_over_budget_summary"):
    assert any(f["name"] == target and f["kind"] == "ensure-unproven"
               for f in negative["findings"]), (target, negative["findings"])
    assert not any(d.get("name") == target and d.get("verified")
                   for d in negative["declaration_details"])
print("bounded predicate summaries, defaults, conjunctions and existential witnesses replay; false, partial and over-budget claims stay open")
