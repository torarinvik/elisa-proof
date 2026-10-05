"""The producer proves and independent replay checks a high-bit u8 logical shift."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/replay_typed_unsigned_shift.elisa"

run = subprocess.run([BINARY, "--json", str(SOURCE)], capture_output=True,
                     text=True, timeout=60)
report = json.loads(run.stdout)
assert run.returncode == 0, (run.returncode, report)
assert report["summary"]["semantic_errors"] == 0, report["summary"]
goals = [goal for goal in report["goals"] if goal["rule"] == "goal"]
assert len(goals) == 2 and all(goal["proven"] for goal in goals), goals
assert all(goal["replay_status"] == "replayed" for goal in goals), goals
assert report["replay"]["certificates"] == report["replay"]["replayed"] == report["summary"]["proven"]
assert report["replay"]["gaps"] == 0 and report["trust"]["trusted_assumptions"] == []

rejected = subprocess.run([BINARY, "--json", str(ROOT / "examples/rejected_typed_unsigned_shift_count.elisa")],
                          capture_output=True, text=True, timeout=60)
rejected_report = json.loads(rejected.stdout)
assert rejected.returncode == 1, rejected_report
rejected_goals = [goal for goal in rejected_report["goals"] if goal["rule"] == "goal"]
assert rejected_goals and not any(goal["proven"] for goal in rejected_goals), rejected_goals
assert rejected_report["replay"]["gaps"] == 0, rejected_report["replay"]
print("u8(128) >> 1 proves as 64 and its certificate independently replays")
