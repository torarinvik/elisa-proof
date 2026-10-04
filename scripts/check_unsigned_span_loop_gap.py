"""Source and independent replay regression for unsigned unit-step descent."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if not __debug__:
    raise SystemExit("run without Python -O")
cases = {
    "unsigned_span_loop_probe.elisa": [],
    "unsigned_span_full_width_probe.elisa": [],
    "unsigned_span_literal_endpoint_probe.elisa": [],
    "rejected_unsigned_span_loop_stalled.elisa": ["loop-decreases-unproven"],
    "rejected_unsigned_span_loop_backward.elisa": ["invariant-not-preserved", "loop-decreases-unproven"],
    "rejected_unsigned_span_descent_guards.elisa": ["ensure-unproven"] * 3,
    "rejected_unsigned_span_literal_endpoint.elisa": ["ensure-unproven"] * 2,
}
for name, expected in cases.items():
    run = subprocess.run([str(ROOT / "build/elisa-proof"), "--json", str(ROOT / "test" / name)],
                         capture_output=True, text=True, timeout=60)
    r = json.loads(run.stdout)
    assert run.returncode == (1 if expected else 0) and r["summary"]["semantic_errors"] == 0
    assert [f["kind"] for f in r["findings"]] == expected
    assert r["replay"]["certificates"] == r["replay"]["replayed"] and r["replay"]["gaps"] == 0
    assert not r["trust"]["trusted_assumptions"]
print("Unsigned named/literal loop descent proves and replays; seven false-step/guard claims reject")
