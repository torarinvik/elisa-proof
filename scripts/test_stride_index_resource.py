import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, expected in (
    ("stride_index_write_probe.elisa", [("rejected_stride_index_write_missing_bound", "index-upper-unproven")]),
    ("stride_index_borrow_probe.elisa", [("stride_index_borrow_disjoint", "borrow-overlap-unproven"),
                                       ("rejected_stride_index_borrow_same_element", "borrow-overlap-unproven")])):
    run = subprocess.run([str(ROOT / "build/elisa-proof"), "--json", str(ROOT / "test" / fixture)],
                         capture_output=True, text=True, timeout=60)
    r = json.loads(run.stdout)
    assert run.returncode == 1 and r["summary"]["semantic_errors"] == 0
    assert [(f["name"], f["kind"]) for f in r["findings"]] == expected
    assert r["replay"]["certificates"] == r["replay"]["replayed"] and r["replay"]["gaps"] == 0
    assert not r["trust"]["trusted_assumptions"]
    if fixture == "stride_index_write_probe.elisa":
        for name in ("stride_index_write", "stride_index_write_offset"):
            goals = [g for g in r["goals"] if g["name"] == name]
            assert goals and all(g["proven"] and g["replay_status"] == "replayed" for g in goals), name
print("Stride writes replay; missing bounds and same-element borrows reject; adjacent separation OPEN")
