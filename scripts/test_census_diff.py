"""Census diff comparison tests: fewer proved goals, a new gate, and a lost report fail; gains pass."""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = {"examples": 2, "proven": 5, "obligations": 6, "unreadable": [], "gates": {"no-rule": 1},
        "files": {"a.elisa": {"proven": 3, "obligations": 3, "gates": [], "seconds": 4.0},
                  "b.elisa": {"proven": 2, "obligations": 3, "gates": ["no-rule"]}}}


def diff(current):
    with tempfile.TemporaryDirectory() as scratch:
        base_path, cur_path = Path(scratch) / "base.json", Path(scratch) / "cur.json"
        base_path.write_text(json.dumps(BASE))
        cur_path.write_text(json.dumps(current))
        return subprocess.run([sys.executable, str(ROOT / "scripts/census_diff.py"), str(base_path), str(cur_path)],
                              capture_output=True, text=True)


def variant(edit):
    current = copy.deepcopy(BASE)
    edit(current)
    return current


assert diff(BASE).returncode == 0
gain = diff(variant(lambda c: c["files"]["b.elisa"].update(proven=3, gates=[])))
assert gain.returncode == 0 and "census gain: b.elisa" in gain.stdout, gain.stdout
drop = diff(variant(lambda c: c["files"]["a.elisa"].update(proven=2)))
assert drop.returncode == 1 and "a.elisa: proven 3 -> 2" in drop.stderr, drop.stderr
gate = diff(variant(lambda c: c["files"]["b.elisa"].update(gates=["no-rule", "budget"])))
assert gate.returncode == 1 and "new refusal gates ['budget']" in gate.stderr, gate.stderr

slow = diff(variant(lambda c: c["files"]["a.elisa"].update(seconds=13.5)))
assert slow.returncode == 1 and "a.elisa: wall time 4.0s -> 13.5s" in slow.stderr, slow.stderr
assert diff(variant(lambda c: c["files"]["a.elisa"].update(seconds=12.5))).returncode == 0


def lose(c):
    del c["files"]["a.elisa"]
    c["unreadable"] = ["a.elisa"]


lost = diff(variant(lose))
assert lost.returncode == 1 and "no longer produces a readable report" in lost.stderr, lost.stderr


def delete_input(c):
    del c["files"]["a.elisa"]


deleted = diff(variant(delete_input))
assert deleted.returncode == 1 and "source is absent" in deleted.stderr, deleted.stderr
print("census diff: drops, new gates, 2x slowdowns, unreadable/missing inputs fail; gains pass")
