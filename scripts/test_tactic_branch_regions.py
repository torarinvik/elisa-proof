"""Exercise scratch-region children through nested split/cases and refusal."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
for fixture in ("branch", "nested_branch", "nested_cases", "branch_incomplete"):
    expected = 1 if fixture == "branch_incomplete" else 0
    run = subprocess.run([str(BINARY), "--tactics",
                          str(ROOT / "examples" / f"tactic_script_{fixture}.json"),
                          str(ROOT / "examples/verified.elisa")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected, (fixture, run.returncode, run.stderr)
    data = json.loads(run.stdout)
    if expected == 0:
        assert data["status"] == "proved", data
        assert data["tactic"]["branch_certificate_replayed"] is True, data
    else:
        assert data["status"] != "proved", data
        assert data["tactic"]["branch_certificate_replayed"] is False, data

# Adversarial isolation. Branch states at one depth reuse a single scratch slot, so a right
# subtree runs in storage its left sibling's subtree already filled. A hypothesis introduced on
# the left must never be visible on the right, even through that reused slot.
X = {"kind": "ident", "name": "x", "line": 1}
NONNEG = {"kind": "binary", "operator": ">=", "left": X, "right": {"kind": "int", "value": 0}}
IMPLIES = {"kind": "binary", "operator": "=>", "left": NONNEG, "right": NONNEG}
TRUE = {"kind": "bool", "value": True}
FACTS = json.loads((ROOT / "examples/tactic_script.json").read_text())["initial"]["facts"]


def conj(left, right):
    return {"kind": "binary", "operator": "and", "left": left, "right": right}


def split(left_actions, right_actions):
    return {"action": "split", "branches": [{"actions": left_actions}, {"actions": right_actions}]}


def run_script(script, tmp_name):
    path = Path(os.environ.get("TMPDIR", "/tmp")) / tmp_name
    path.write_text(json.dumps(script))
    run = subprocess.run([str(BINARY), "--tactics", str(path), str(ROOT / "examples/verified.elisa")],
                         capture_output=True, text=True, timeout=120)
    return run.returncode, json.loads(run.stdout)


def isolation_script(right_goal, right_actions):
    left = split([{"action": "intro"}, {"action": "exact"}], [{"action": "decide"}])
    right = split(right_actions, [{"action": "decide"}])
    return {"format": "elisa-proof-tactics-v1",
            "initial": {"facts": FACTS, "goal": conj(conj(IMPLIES, TRUE), conj(right_goal, TRUE))},
            "actions": [split([left], [right])]}


# Positive control: the reused slot is reinitialized and can host an independent valid proof.
code, data = run_script(isolation_script(IMPLIES, [{"action": "intro"}, {"action": "exact"}]), "branch_reuse_valid.json")
assert code == 0 and data["status"] == "proved", data
assert data["tactic"]["branch_certificate_replayed"] is True, data

# The left sibling introduced x >= 0; the right sibling's bare x >= 0 goal must not see it.
code, data = run_script(isolation_script(NONNEG, [{"action": "exact"}]), "branch_sibling_leak.json")
assert code == 1 and data["status"] != "proved", data
assert data["tactic"]["solved"] is False and data["tactic"]["branch_certificate_replayed"] is False, data
assert data["tactic"]["valid"] is False, data
assert data["tactic"]["reason"] == "tactic action outcome contradicted the script's expected acceptance", data
code, data = run_script(isolation_script(NONNEG, [{"action": "exact", "accepted": False}]), "branch_sibling_refused.json")
assert code == 1 and data["status"] != "proved", data
assert data["tactic"]["valid"] is True, data
assert data["tactic"]["branch_certificate_replayed"] is False, data


# Depth exhaustion: nesting at the limit is refused as invalid instead of overrunning scratch.
def nested(depth):
    goal = TRUE
    for _ in range(depth + 1):
        goal = conj(goal, TRUE)
    actions = [{"action": "decide"}]
    for _ in range(depth + 1):
        actions = [split(actions, [{"action": "decide"}])]
    return {"format": "elisa-proof-tactics-v1", "initial": {"facts": [], "goal": goal}, "actions": actions}


BRANCH_DEPTH_LIMIT = 32
code, data = run_script(nested(BRANCH_DEPTH_LIMIT - 1), "branch_depth_ok.json")
assert code == 0 and data["status"] == "proved", data
code, data = run_script(nested(BRANCH_DEPTH_LIMIT), "branch_depth_exhausted.json")
assert code == 1 and data["status"] != "proved", data
assert data["tactic"]["valid"] is False and data["tactic"]["solved"] is False, data
assert data["tactic"]["reason"] == "tactic script exhausted its branch depth or tree node budget", data
print("tactic branch regions: nested replay, sibling isolation, slot reuse, and depth exhaustion passed")
