"""An unrelated Boolean early return must retain counted prefix induction."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
p = subprocess.run([BIN, "--function-json", "counted_prefix_boolean_branch_probe",
                    str(ROOT / "examples/counted_prefix_framed_boolean_probe.elisa")],
                   capture_output=True, text=True, timeout=60)
r = json.loads(p.stdout)
assert p.returncode == 0 and r["status"] == "proved", r["findings"]
assert r["summary"]["semantic_errors"] == 0
assert r["summary"]["obligations"] == r["summary"]["proven"] == 21
assert r["replay"]["certificates"] == r["replay"]["replayed"] == 21
assert r["replay"]["gaps"] == 0 and not r["findings"]
assert not r["trust"]["trusted_assumptions"]
print("Boolean-parameter prefix branch replays; framed-call diagnostic remains open")
