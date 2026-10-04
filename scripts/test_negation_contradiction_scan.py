"""Failed negation queries must not become invented contradictory premises."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("negation_contradiction_scan.elisa", True),
                          ("rejected_negation_contradiction_scan.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), r["findings"]
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["summary"]["semantic_errors"] == 0
        assert r["status"] == "proved" and not r["findings"]
    else:
        for name in ("rejected_positive_boolean_path", "rejected_negative_boolean_path",
                     "rejected_nonnegated_arithmetic"):
            assert any(f["name"] == name and f["kind"] == "ensure-unproven"
                       for f in r["findings"]), (name, r["findings"])
            assert not any(d.get("name") == name and d.get("verified")
                           for d in r["declaration_details"])
print("contradictory Boolean paths replay; reachable and arithmetic false paths reject")
