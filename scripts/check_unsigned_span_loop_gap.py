"""Baseline reproducer; expected open until source and kernel descent support."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if not __debug__:
    raise SystemExit("run without Python -O")
cases = {
    "unsigned_span_loop_probe.elisa": ["loop-decreases-unproven", "ensure-unproven"],
    "rejected_unsigned_span_loop_stalled.elisa": ["loop-decreases-unproven"],
    "rejected_unsigned_span_loop_backward.elisa": ["invariant-not-preserved", "loop-decreases-unproven"],
}
for name, expected in cases.items():
    run = subprocess.run([str(ROOT / "build/elisa-proof"), "--json", str(ROOT / "test" / name)],
                         capture_output=True, text=True, timeout=60)
    r = json.loads(run.stdout)
    assert run.returncode == 1 and r["summary"]["semantic_errors"] == 0
    assert [f["kind"] for f in r["findings"]] == expected
    assert r["replay"]["certificates"] == r["replay"]["replayed"] and r["replay"]["gaps"] == 0
    assert not r["trust"]["trusted_assumptions"]
print("OPEN unsigned loop descent isolated; stalled and backward controls reject")
