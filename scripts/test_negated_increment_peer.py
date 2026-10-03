"""Complemented unsigned peer bounds replay; overflow and width gaps stay refused."""
import collections
import json
import os
from pathlib import Path
import subprocess
if not __debug__:
    raise SystemExit("run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
p = subprocess.run([binary, "--json", str(ROOT / "test/negated_increment_peer.elisa")], capture_output=True, text=True, timeout=60)
r = json.loads(p.stdout)
assert p.returncode == 1 and r["summary"]["semantic_errors"] == 0
assert not r["trust"]["trusted_assumptions"]
assert r["replay"] == {"certificates": 10, "replayed": 10, "gaps": 0}
for name in ("guarded_forward", "guarded_reverse"):
    goals = [g for g in r["goals"] if g["name"] == name]
    assert goals and all(g["proven"] and g["replay_status"] == "replayed" for g in goals)
for name in ("false_unguarded_progress", "false_mixed_width", "false_equal_progress"):
    assert any(not g["proven"] for g in r["goals"] if g["name"] == name)
assert collections.Counter((f["name"], f["kind"]) for f in r["findings"]) == {
    ("false_unguarded_progress", "ensure-unproven"): 1,
    ("false_mixed_width", "ensure-unproven"): 2,
    ("false_equal_progress", "ensure-unproven"): 1,
}
print("negated increment peers: guarded positives replay; overflow, mixed-width and equal-progress negatives reject")
