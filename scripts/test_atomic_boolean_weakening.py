"""Context weakening cannot invent truth or discard the full-context fallback."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("atomic_boolean_weakening.elisa", True),
                          ("rejected_atomic_boolean_weakening.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), r["findings"]
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["summary"]["semantic_errors"] == 0, r["semantic_diagnostics"]
        assert r["status"] == "proved" and not r["findings"]
    else:
        for name in ("rejected_unknown_boolean", "rejected_boolean_polarity",
                     "rejected_arithmetic_boolean_path"):
            assert any(f["name"] == name and f["kind"] == "ensure-unproven"
                       for f in r["findings"]), (name, r["findings"])
            assert not any(d.get("name") == name and d.get("verified")
                           for d in r["declaration_details"])
print("atomic Boolean weakening replays; full-context fallback and false controls pass")
