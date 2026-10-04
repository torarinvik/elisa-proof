"""Negated closed signed comparisons must evaluate exactly on both proof paths."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")

for fixture, expected in (("signed_literal_negation.elisa", "proved"),
                          ("rejected_signed_literal_negation.elisa", "failed")):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert report["status"] == expected, report["findings"]
    assert result.returncode == (0 if expected == "proved" else 1)
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    if expected == "proved":
        assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
    else:
        for target in ("rejected_signed_literal_negation", "rejected_signed_literal_identity_negation"):
            assert any(f["name"] == target and f["kind"] == "ensure-unproven"
                       for f in report["findings"]), report["findings"]
print("closed signed literal negations independently replay; false order and identity negations reject")
