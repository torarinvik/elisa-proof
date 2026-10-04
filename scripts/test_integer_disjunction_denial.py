"""Integer type-witnessed total ordering, without assuming float total order."""
import json
import os
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O: regression assertions must remain enabled")

def run(name):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)

code, report = run("integer_disjunction_denial_probe.elisa")
assert code == 0 and report["status"] == "proved", report["findings"]
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
code, report = run("integer_disjunction_denial_rejected.elisa")
assert code == 1 and report["status"] == "failed"
assert report["summary"]["semantic_errors"] == 0
for name in ("integer_denial_false", "integer_denial_float", "integer_denial_float_field"):
    assert any(f["name"] == name and f["kind"] in ("ensure-unproven", "contract-proposition-type", "contract-expression-unsupported")
               for f in report["findings"]), report["findings"]
assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
print("integer-witnessed ordering denial replays; false integer and float total-order claims rejected")
