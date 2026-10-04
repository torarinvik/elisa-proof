"""Signed ghost endpoints must not admit unsigned negation or wrapped tokens."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
run = subprocess.run(
    [BIN, "--json", str(ROOT / "examples/rejected_quantifier_unsigned_negative_bounds.elisa")],
    capture_output=True, text=True, timeout=60,
)
report = json.loads(run.stdout)
assert run.returncode == 1, (run.returncode, run.stderr)
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"]
assert not report["trust"]["trusted_assumptions"]
for name in ("rejected_unsigned_negative_lower", "rejected_unsigned_negative_upper",
             "rejected_wrapped_payload_endpoint"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven"
               for f in report["findings"]), report["findings"]
    assert not any(d.get("name") == name and d.get("verified")
                   for d in report["declaration_details"])
print("quantifier endpoints reject unsigned wrap and untyped high-bit payloads")
