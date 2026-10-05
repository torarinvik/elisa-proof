"""Every unproven goal and its finding name the first guard that refuses it (BACKLOG A-02).
The field is diagnostic only: proven goals carry none, and the gate never changes a verdict."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
GATES = {"unknown", "kernel-replay-gap", "budget", "literal-width", "ambiguous-constant-goal", "wrap-guard-fact",
         "wrap-guard-goal", "quantifier", "overloaded-operator", "connective",
         "non-comparison-goal", "opaque-call-goal"}


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode in (0, 1), (name, result.returncode, result.stderr)
    return json.loads(result.stdout)


def check_ensure_gates(data):
    goals = {goal["goal_id"]: goal for goal in data["goals"]}
    for finding in data["findings"]:
        if finding["kind"] != "ensure-unproven":
            continue
        assert finding.get("refusal_gate") in GATES, finding
        goal_id = finding.get("goal_id")
        if goal_id is not None and goal_id in goals:
            assert not goals[goal_id]["proven"], (finding, goals[goal_id])
            assert goals[goal_id].get("refusal_gate") in GATES, (finding, goals[goal_id])


def gates(name):
    data = run(name)
    check_ensure_gates(data)
    return [f.get("refusal_gate") for f in data["findings"]
            if f["kind"] == "ensure-unproven"]


assert gates("rejected_signed_lower_bound.elisa") == ["budget", "literal-width", "literal-width"]
assert gates("rejected_variant_exclusion.elisa") == ["non-comparison-goal"]
assert gates("rejected_qualified_body_shadow.elisa") == ["wrap-guard-goal"]
assert gates("branch_conjunct_placeholder.elisa") == ["unknown"]

data = run("signed_lower_bound.elisa")
assert data["findings"] == [] and all("refusal_gate" not in g for g in data["goals"])
for name in ("rejected_signed_upper_bound.elisa", "rejected_variant_exclusion_ambiguous.elisa"):
    data = run(name)
    check_ensure_gates(data)
    for goal in data["goals"]:
        assert ("refusal_gate" in goal) == (not goal["proven"]), goal
        assert goal.get("refusal_gate", "budget") in GATES, goal
print("refusal gate: unproven goals name their first refusing guard; proven goals carry none")
