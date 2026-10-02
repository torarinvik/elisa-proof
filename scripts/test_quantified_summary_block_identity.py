"""Quantified source summary identity must replay without equating forall/exists."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("quantified_summary_block_identity.elisa", True),
                          ("rejected_quantified_summary_block_identity.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), r["findings"]
    assert r["replay"]["gaps"] == 0, r["replay"]
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["summary"]["semantic_errors"] == 0
        assert r["status"] == "proved" and not r["findings"]
    else:
        assert any(f["name"] == "rejected_existential_as_universal" and f["kind"] == "ensure-unproven"
                   for f in r["findings"]), r["findings"]
        assert not any(d.get("name") == "rejected_existential_as_universal" and d.get("verified")
                       for d in r["declaration_details"])
print("quantified summary block identity replays; existential-to-universal claim rejects")
