"""The same conditional result is split under its guard and negation, fail-closed."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("conditional-result regression must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/conditional_result_branchwise_probe.elisa"

run = subprocess.run([str(BINARY), "--json", str(SOURCE)], capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["status"] == "failed", report
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["trust"]["trusted_assumptions"] == [], report["trust"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
assert any(goal["name"] == "conditional_result_both_arms" and goal["proven"]
           and goal["replay_status"] == "replayed" for goal in report["goals"]), report["goals"]
findings = [(item["name"], item["kind"]) for item in report["findings"]]
assert findings == [
    ("rejected_conditional_result_bad_arm", "ensure-unproven"),
    ("rejected_conditional_result_altered_guard", "ensure-unproven"),
    ("rejected_conditional_result_fuel", "ensure-unproven"),
], findings
details = {item["name"]: item for item in report["findings"]}
assert details["rejected_conditional_result_altered_guard"]["refusal_gate"] == "connective", details
assert details["rejected_conditional_result_fuel"]["refusal_gate"] == "budget", details
print("conditional result replay: both guarded arms replay; bad arm, altered guard, and split-fuel controls refuse without gaps")
