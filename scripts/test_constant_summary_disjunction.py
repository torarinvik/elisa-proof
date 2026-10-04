"""Return widths describe call results, not their independently typed arguments."""
import collections
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
p = subprocess.run([binary, "--json", str(ROOT / "test/constant_summary_disjunction.elisa")],
                   capture_output=True, text=True, timeout=60)
r = json.loads(p.stdout)
assert p.returncode == 1 and r["summary"]["semantic_errors"] == 0
assert not r["trust"]["trusted_assumptions"]
assert r["replay"] == {"certificates": 42, "replayed": 42, "gaps": 0}
for name in ("valid_summary_caller", "valid_wide_summary_caller",
             "valid_four_argument_caller", "exact_four_argument_caller"):
    goals = [g for g in r["goals"] if g["name"] == name]
    assert goals and all(g["proven"] and g["replay_status"] == "replayed" for g in goals)
negatives = ("rejected_summary_caller", "rejected_wide_summary_caller", "rejected_call_arithmetic_wrap")
for name in negatives:
    assert any(not g["proven"] for g in r["goals"] if g["name"] == name)
assert collections.Counter((f["name"], f["kind"]) for f in r["findings"]) == {
    (name, "ensure-unproven"): 1 for name in negatives
}
print("call result widths: large u32/u64 arguments replay; false result and wrapping arithmetic controls reject")
