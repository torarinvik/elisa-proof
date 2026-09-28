"""Regression for guarded subtraction, including independent replay and refusals."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name, expected):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected, (name, run.returncode, run.stderr)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["replay"]["gaps"] == 0, data
    assert data["replay"]["replayed"] == data["replay"]["certificates"], data
    return data


positive = report("guarded_unsigned_subtraction_upper.elisa", 0)
assert positive["verification_state"] == "proved"
for name in ("guarded_word", "guarded_byte"):
    assert any(g["name"] == name and g["rule"] == "goal" and
               g["proven"] and g["replay_status"] == "replayed"
               for g in positive["goals"]), name

negative = report("rejected_unsigned_subtraction_upper.elisa", 1)
for name in ("unguarded_word", "zero_is_not_strict_decrease", "signed_negative_subtrahend"):
    assert any(f["name"] == name for f in negative["findings"]), name
    assert not any(g["name"] == name and g["rule"] == "goal" and g["proven"]
                   for g in negative["goals"]), name
print("guarded unsigned subtraction: positive replay and three rejection controls passed")
