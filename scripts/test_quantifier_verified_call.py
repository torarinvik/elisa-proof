"""Admit verified predicate syntax without admitting impure or false contracts."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def run(fixture, semantic_errors=0):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=90)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == semantic_errors, report
    assert report["replay"]["gaps"] == 0, report
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report
    assert not report["trust"]["trusted_assumptions"], report
    return result.returncode, report


code, positive = run("quantifier_verified_call.elisa")
assert code == 0 and positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0
assert not positive["findings"], positive

code, negative = run("rejected_quantifier_verified_call.elisa")
assert code == 1 and negative["status"] == "failed", negative
for target, kind in (
    ("rejected_false_quantified_call", "ensure-unproven"),
    ("rejected_unverified_quantified_call", "contract-call-unsupported"),
    ("rejected_impure_quantified_call", "contract-call-unsupported"),
):
    assert any(f["name"] == target and f["kind"] == kind
               for f in negative["findings"]), (target, negative)
    assert not any(d.get("kind") == "function" and d.get("name") == target
                   and d.get("verified") for d in negative["declaration_details"])
code, shadow = run("rejected_quantifier_callable_shadow.elisa", semantic_errors=1)
assert code == 1 and shadow["status"] == "failed", shadow
assert any(f["name"] == "rejected_callable_shadow" and f["kind"] == "contract-expression-unsupported"
           for f in shadow["findings"])
assert not any(d.get("name") == "rejected_callable_shadow" and d.get("verified")
               for d in shadow["declaration_details"])
code, ambiguous = run("rejected_quantifier_call_ambiguity.elisa")
assert code == 1 and ambiguous["status"] == "failed", ambiguous
assert any(f["name"] == "rejected_ambiguous_quantified_calls"
           and f["kind"] == "contract-proposition-type" for f in ambiguous["findings"])
assert not any(d.get("name") == "rejected_ambiguous_quantified_calls" and d.get("verified")
               for d in ambiguous["declaration_details"])
print("verified quantified predicate hypotheses replay; false, unverified, impure, callable-shadow and ambiguous-head controls reject")
