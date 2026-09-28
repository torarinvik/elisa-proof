"""Disjunction introduction must not bypass arithmetic guards on consumed terms."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def report(fixture, expected):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / fixture)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected, (run.returncode, run.stderr)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["replay"]["gaps"] == 0, data
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data
    return data


positive = report("unsigned_disjunction_introduction.elisa", 0)
assert positive["verification_state"] == "proved", positive
assert positive["summary"]["obligations"] == positive["summary"]["proven"] > 0
negative = report("rejected_unsigned_disjunction.elisa", 1)
for name in ("wrapping_or_false_identity", "false_identity_or_wrapping"):
    assert any(f["name"] == name and f["kind"] == "proof-unproven"
               for f in negative["findings"]), negative
    claims = [g for g in negative["goals"] if g["name"] == name and
              g["rule"] == "goal" and g["goal"].get("operator") == "or"]
    assert len(claims) == 1 and claims[0]["proven"] is False, name
print("unsigned disjunction: both identity alternatives replayed; wrapping false claims refused")
