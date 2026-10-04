import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if not __debug__:
    raise SystemExit("run without Python -O")
run = subprocess.run([str(ROOT / "build/elisa-proof"), "--json",
                      str(ROOT / "test/fixed_array_extent_after_loop_probe.elisa")],
                     capture_output=True, text=True, timeout=60)
r = json.loads(run.stdout)
assert run.returncode == 1 and r["summary"]["semantic_errors"] == 0
assert r["replay"]["certificates"] == r["replay"]["replayed"] == 40
assert r["replay"]["gaps"] == 0 and not r["trust"]["trusted_assumptions"]
assert [(f["name"], f["kind"]) for f in r["findings"]] == [
    ("rejected_fixed_array_after_loop_out_of_bounds", "index-upper-unproven"),
    ("rejected_fixed_array_stale_element_after_loop", "ensure-unproven")]
for name in ("fixed_array_extent_after_loop", "fixed_array_extent_after_for_loop"):
    goals = [g for g in r["goals"] if g["name"] == name]
    assert goals and all(g["proven"] and g["replay_status"] == "replayed" for g in goals)
print("Declared fixed extents survive while/for loops; out-of-bounds and stale elements reject")
