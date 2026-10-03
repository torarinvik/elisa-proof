"""Contextual conditional branch typing must preserve exact values and polarity."""
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
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == 0, report
    assert report["replay"]["gaps"] == 0, report
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report
    assert not report["trust"]["trusted_assumptions"], report
    assert not any(f["kind"] == "contract-proposition-type" for f in report["findings"]), report
    return result.returncode, report

code, positive = run("conditional_unsigned_literal.elisa")
assert code == 0 and positive["status"] == "proved", positive
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0
code, negative = run("rejected_conditional_unsigned_literal.elisa")
assert code == 1 and negative["status"] == "failed", negative
for name in ("false_conditional_polarity", "false_conditional_wrap"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven"
               for f in negative["findings"]), name
    assert not any(d.get("name") == name and d.get("verified")
                   for d in negative["declaration_details"]), name
print("Unsigned conditional literals replay; false polarity and value controls reject")
