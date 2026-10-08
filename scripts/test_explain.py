"""`--explain <goal_id>` prints one goal, its verdict, the refusing gate and every fact with its
recorded origin. The open-goal rendering is pinned as a snapshot; the JSON report is the source of
truth for gates and fact counts, and bad or missing ids exit 2 without a rendering."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("explanation checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(*arguments):
    result = subprocess.run([str(BINARY), *arguments], capture_output=True, text=True, timeout=120)
    return result.returncode, result.stdout


OPEN = ROOT / "examples/rejected_front_end_diagnostic_engine_open.elisa"
SNAPSHOT = """goal 2 in keep line 6 (goal)
  goal: x > x
  verdict: open, refused at gate budget
  facts: 4
    [0] __elisa_signed_type_bound(x, 8)  <- type-bound line 3
    [1] x <= 127  <- type-bound line 3
    [2] (-127 - 1) <= x  <- type-bound line 3
    [3] __elisa_primitive_scalar_type(x)  <- type-bound line 3
"""
status, text = run("--explain", "2", str(OPEN))
assert status == 1 and text == SNAPSHOT, text

status, text = run("--explain", "0", str(ROOT / "examples/literal_count.elisa"))
assert status == 0 and "verdict: proven, replayed certificate 0\n" in text, text

# A producer certificate can rest on a premise independent replay has no source route for (here
# a loop-exit fact about a captured loop result), leaving a replay gap. The human-facing
# verdict must expose that refusal, not the producer's provisional result.
GAP = ROOT / "examples/rejected_global_constant_loop_exit.elisa"
status, raw = run("--json", str(GAP))
report = json.loads(raw)
assert status == 1 and report["replay"]["gaps"] > 0, report["replay"]
gaps = [goal for goal in report["goals"] if goal.get("replay_status") == "gap"]
assert gaps, report["goals"]
for goal in gaps:
    status, text = run("--explain", str(goal["goal_id"]), str(GAP))
    assert status == 1, (status, text)
    assert "verdict: not proven: producer result lacks successful kernel replay\n" in text, text
    assert "verdict: proven" not in text, text

# Every open goal of the budget fixture names the same gate the JSON report does, and lists
# exactly the facts the report carries.
BUDGET = ROOT / "examples/rejected_budget.elisa"
_, raw = run("--json", str(BUDGET))
for goal in json.loads(raw)["goals"]:
    status, text = run("--explain", str(goal["goal_id"]), str(BUDGET))
    if goal["proven"]:
        assert goal["replay_status"] == "replayed", goal
        assert "verdict: proven, replayed certificate " in text, text
    else:
        assert "refused at gate %s\n" % goal["refusal_gate"] in text, text
    assert "  facts: %d\n" % len(goal["facts"]) in text and text.count("\n    [") == len(goal["facts"])

for arguments, expected in (
    (("--explain", "99", str(OPEN)), "elisa-proof: no goal 99 in this report\n"),
    (("--explain", "x", str(OPEN)), "elisa-proof: goal id must be an unsigned 32-bit integer\n"),
    (("--explain", "-1", str(OPEN)), "elisa-proof: goal id must be an unsigned 32-bit integer\n"),
    (("--explain", "2"), "usage: elisa-proof --explain <goal_id> <file.elisa>\n"),
):
    status, text = run(*arguments)
    assert status == 2 and text == expected, (arguments, status, text)

print("explain: one goal, its gate and its facts with their origins")
