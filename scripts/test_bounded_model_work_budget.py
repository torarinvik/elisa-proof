"""The bounded model evaluator refuses frames above its measured work cap."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
FIXTURE = ROOT / "examples/bounded_model_work_budget.elisa"
STRESS_CLAUSE = "requires ModelBudgetConstants::C == ModelBudgetConstants::C"
UNDER_BUDGET_STRESS_COUNT = 12
OVER_BUDGET_STRESS_COUNT = 20


def stress_clause_count(function_name: str) -> int:
    source = FIXTURE.read_text(encoding="utf-8")
    function_start = source.index(f"def {function_name}(")
    next_function = source.find("\ndef ", function_start + 1)
    function_source = source[function_start:] if next_function < 0 else source[function_start:next_function]
    return sum(line.strip() == STRESS_CLAUSE for line in function_source.splitlines())


assert stress_clause_count("bounded_model_under_work_budget") == UNDER_BUDGET_STRESS_COUNT
assert stress_clause_count("bounded_model_over_work_budget") == OVER_BUDGET_STRESS_COUNT


result = subprocess.run(
    [str(BINARY), "--json", str(FIXTURE)],
    capture_output=True,
    text=True,
    timeout=60,
)
assert result.returncode == 1, (result.returncode, result.stderr)
report = json.loads(result.stdout)
assert report["status"] == "failed" and report["verification_state"] == "unknown", report
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]

goals = {
    (goal["name"], goal["rule"]): goal
    for goal in report["goals"]
}
within = goals[("bounded_model_under_work_budget", "goal")]
assert within["proven"] and within["replay_status"] == "replayed", within
over = goals[("bounded_model_over_work_budget", "goal")]
assert not over["proven"] and over["certificate_id"] is None, over
assert over["refusal_gate"] == "budget", over

finding = next(
    row for row in report["findings"]
    if row["name"] == "bounded_model_over_work_budget" and row["kind"] == "ensure-unproven"
)
assert finding["status"] == "timeout" and not finding["counterexample_found"], finding
assert finding["counterexample"] == [], finding

print("bounded model work budget: in-budget fixture proves; over-budget fixture refuses without a model or replay gap")
