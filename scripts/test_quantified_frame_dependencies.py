"""Frames retain disjoint quantified facts, never stale changed-root facts."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("quantified_frame_dependencies.elisa", True),
                          ("rejected_quantified_frame_dependencies.elisa", False),
                          ("framed_call.elisa", True), ("indexed_frame.elisa", True),
                          ("rejected_frame_alias.elisa", False), ("rejected_frame_preserve.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), (fixture, r["findings"])
    assert r["summary"]["semantic_errors"] == 0
    assert r["replay"]["gaps"] == 0 and r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["status"] == "proved" and not r["findings"]
    if fixture == "rejected_quantified_frame_dependencies.elisa":
        assert any(f["name"] == "rejected_changed_quantified_rows" and f["kind"] == "ensure-unproven" for f in r["findings"])
        assert any(d.get("name") == "invalidate_rows" and d.get("verified") for d in r["declaration_details"])
print("disjoint quantified and literal facts survive checked frames; changed-root, alias and preserve controls reject")
