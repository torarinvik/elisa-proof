"""Repeated fact growth remains visible alongside theorem-relevant premises."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
FIXTURE = ROOT / "examples/fact_growth_work_budget.elisa"

result = subprocess.run([str(BINARY), "--json", str(FIXTURE)], capture_output=True,
                        text=True, timeout=60)
report = json.loads(result.stdout)
assert result.returncode == 1, (result.returncode, report)
assert report["status"] == "failed" and report["verification_state"] == "unknown", report
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]

goals = {(goal["name"], goal["rule"]): goal for goal in report["goals"]}
within = goals[("fact_growth_under_work_budget", "goal")]
assert within["proven"] and within["replay_status"] == "replayed", within
over = goals[("fact_growth_over_work_budget", "goal")]
assert not over["proven"] and over["certificate_id"] is None, over
assert over["refusal_gate"] == "budget", over
finding = next(row for row in report["findings"]
               if row["name"] == "fact_growth_over_work_budget"
               and row["kind"] == "ensure-unproven")
assert finding["status"] == "timeout" and not finding["counterexample_found"], finding
assert finding["counterexample"] == [], finding

print("fact growth: relevant-premise case proves below cap; over-cap case refuses without a model or replay gap")
