"""Finite predicate context reduction must not select future or unrelated bytes."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def run(fixture):
    result = subprocess.run(
        [BIN, "--json", str(ROOT / "examples" / fixture)],
        capture_output=True, text=True, timeout=90)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    return result.returncode, report


code, positive = run("finite_predicate_context.elisa")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0
code, negative = run("rejected_finite_predicate_context.elisa")
assert code == 1 and negative["status"] == "failed", negative["findings"]
for name in ("rejected_future_predicate_context", "rejected_other_array_predicate_context",
             "rejected_existential_predicate_context"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven"
               for f in negative["findings"]), negative["findings"]
    assert not any(d.get("name") == name and d.get("verified")
                   for d in negative["declaration_details"])
print("64-element predicate context replays; future, other-array and existential claims reject")
