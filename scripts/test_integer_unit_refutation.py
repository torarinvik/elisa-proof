"""Guarded integer unit propagation, with overflow/float/false controls."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O: assertions must remain enabled")

def run(source, target):
    p = subprocess.run([BIN, "--function-json", target, str(ROOT / "examples" / source)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert r["summary"]["semantic_errors"] == 0
    assert r["replay"]["gaps"] == 0, (target, r["replay"])
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    return p.returncode, r

for target in ("integer_unit_known_or_prefix", "integer_unit_closed", "integer_unit_chain", "integer_unit_alias", "integer_unit_range",
               "integer_unit_signed", "integer_unit_field", "integer_unit_alias_disequality",
               "integer_unit_parenthesized_alias"):
    code, r = run("integer_unit_refutation_probe.elisa", target)
    assert code == 0 and r["status"] == "proved" and not r["findings"], (target, r["findings"])
    assert r["replay"]["replayed"] == 2
for target in ("exact_capture_success", "exact_capture_allocation", "exact_capture_touch",
               "exact_capture_pointer", "exact_capture_success_with_domains"):
    code, r = run("capture_exact_summary_probe.elisa", target)
    assert code == 0 and r["status"] == "proved" and not r["findings"], (target, r["findings"])
    assert r["replay"]["replayed"] == 2
for target in ("integer_unit_wrong_or_prefix", "integer_unit_closed_true", "integer_unit_missing_link", "integer_unit_boundary",
               "integer_unit_float", "integer_unit_wrap"):
    code, r = run("integer_unit_refutation_rejected.elisa", target)
    assert code == 1 and r["status"] == "failed"
    assert any(f["name"] == target and f["kind"] in
               ("ensure-unproven", "contract-proposition-type", "contract-expression-unsupported")
               for f in r["findings"]), (target, r["findings"])
print("integer chains, aliases and ranges replay; missing links, boundary, float and wrap controls reject")
