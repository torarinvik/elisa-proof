"""Replay checks a function-summary dependency by its declaration row: goals, findings, and certificates of a same-named function in another module neither veto nor vouch for the callee, and a bare same-module call to a repeated name replays."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))

run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples" / "replay_dependency_row_probe.elisa")],
    capture_output=True, text=True, timeout=60,
)
assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] == report["summary"]["proven"], report["replay"]
for goal in report["goals"]:
    assert goal["proven"] == (goal["replay_status"] == "replayed"), goal["name"]
proven = {goal["name"] for goal in report["goals"] if goal["proven"]}
assert {"locked", "range_step", "step", "apply"} <= proven, proven
kinds = {(finding["name"], finding["kind"]) for finding in report["findings"]}
assert kinds == {("apply", "call-requires-unproven")}, kinds

print("replay dependency row: same-named rows keyed apart; bare same-module call replays")
