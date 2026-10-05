"""Replay contextual integer-literal equality only inside matching comparisons."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
run = subprocess.run([BINARY, "--json", str(ROOT / "test/typed_integer_summary_disjunction.elisa")],
                     capture_output=True, text=True, timeout=60)
report = json.loads(run.stdout)
assert run.returncode == 1 and report["summary"]["semantic_errors"] == 0, report
assert not report["trust"]["trusted_assumptions"], report["trust"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
valid = [goal for goal in report["goals"] if goal["name"] == "valid_context_typed_summary"]
assert valid and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in valid), valid
rejected = [goal for goal in report["goals"] if goal["name"] == "rejected_different_literal"]
assert rejected and any(not goal["proven"] for goal in rejected), rejected
assert any(finding["name"] == "rejected_different_literal" and finding["kind"] == "ensure-unproven"
           for finding in report["findings"]), report["findings"]
print("context-typed summary literal replays; changed-literal false control remains open")
