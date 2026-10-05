"""Exercise bounded proof work across two logically distinct fixture shapes."""
import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
FIXTURE = ROOT / "examples/r013_logical_work_stress.elisa"

started = time.monotonic()
result = subprocess.run(
    [str(BINARY), "--json", str(FIXTURE)], capture_output=True, text=True, timeout=60
)
wall_seconds = round(time.monotonic() - started, 6)
report = json.loads(result.stdout)
assert result.returncode == 1, (result.returncode, result.stderr)
assert report["status"] == "failed" and report["verification_state"] == "unknown", report
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]

goals = {
    goal["name"]: goal
    for goal in report["goals"]
    if goal["rule"] == "goal"
}
bounded_names = (
    "disjunctive_premises_under_budget",
    "wide_equality_graph_under_budget",
)
refused_names = (
    "disjunctive_premises_over_budget",
    "wide_equality_graph_over_budget",
)
for name in bounded_names:
    goal = goals[name]
    assert goal["proven"] and goal["replay_status"] == "replayed", goal

findings = {
    row["name"]: row
    for row in report["findings"]
    if row["kind"] == "ensure-unproven"
}
for name in refused_names:
    goal = goals[name]
    assert not goal["proven"] and goal["certificate_id"] is None, goal
    assert goal["replay_status"] == "not_certified", goal
    assert name in findings, report["findings"]
    finding = findings[name]
    assert not finding["counterexample_found"] and finding["counterexample"] == [], finding

assert goals["disjunctive_premises_over_budget"]["refusal_gate"] == "budget", goals

# Report only exposed measurements. These describe this invocation and are not
# interpreted as a scaling law or as counts of all internal solver work.
measurements = report.get("measurements", {})
recorded = {
    key: measurements.get(key)
    for key in (
        "producer_disjunction_facts_scanned",
        "producer_disjunction_refutation_checks",
        "control_flow_steps",
        "live_facts_peak",
        "kernel_nodes",
        "report_bytes",
    )
}
assert all(value is not None for value in recorded.values()), recorded
print(json.dumps({"result": "passed", "wall_seconds": wall_seconds,
                  "measurements": recorded}, sort_keys=True))
