"""Unused quantified premises are dropped, never exempted from safety checks."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")

for fixture, expected in (("quantified_premise_weakening.elisa", "proved"),
                          ("rejected_quantified_premise_weakening.elisa", "failed")):
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
        for target in ("rejected_quantified_premise_scalar", "rejected_quantified_wrapping_premise",
                       "rejected_quantified_wrapping_range"):
            assert any(f["name"] == target and f["kind"] == "ensure-unproven"
                       for f in report["findings"]), (target, report["findings"])
probe = subprocess.run([BIN, "--json", str(ROOT / "examples/open_history_length_prefix.elisa")],
                       capture_output=True, text=True, timeout=60)
report = json.loads(probe.stdout)
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"]
assert not report["trust"]["trusted_assumptions"]
assert any(d.get("name") == "scalar_with_quantified_prefix" and d.get("verified")
           for d in report["declaration_details"]), report["findings"]
# The real loop-prefix induction requirement is retained, not inferred from
# success on scalar arithmetic and not replaced with an alternate scanner.
assert any(f["name"] == "history_length_prefix" and f["kind"] == "ensure-unproven"
           for f in report["findings"]), report["findings"]
print("scalar arithmetic independently replays after quantified-premise weakening; false conclusions reject; prefix induction remains open")
