"""Impossible integer branches replay without accepting float or wrap claims."""
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

for target in ("capture_result_alias", "capture_result_direct"):
    code, r = run("capture_result_alias_probe.elisa", target)
    assert code == 0 and r["status"] == "proved" and not r["findings"]
    assert r["replay"]["replayed"] == 2
for target in ("capture_result_missing_link", "capture_result_wrong_output",
               "capture_result_float_interval", "capture_result_unsigned_wrap",
               "capture_result_signed_wrap"):
    code, r = run("capture_result_alias_rejected.elisa", target)
    assert code == 1 and r["status"] == "failed"
    assert any(f["name"] == target and f["kind"] in
               ("ensure-unproven", "contract-proposition-type", "contract-expression-unsupported")
               for f in r["findings"]), (target, r["findings"])
print("integer summary branches replay; missing links, false outputs, float intervals and wrap controls reject")
