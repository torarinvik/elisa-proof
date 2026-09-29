"""Every unproven goal and its finding name the first guard that refuses it (BACKLOG A-02).
The field is diagnostic only: proven goals carry none, and the gate never changes a verdict."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
GATES = {"budget", "literal-width", "ambiguous-constant-goal", "ambiguous-constant-fact", "wrap-guard-fact",
         "wrap-guard-goal", "quantifier", "overloaded-operator", "no-rule", "connective",
         "non-comparison-goal", "opaque-call-goal"}


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


def gates(name):
    return [f.get("refusal_gate") for f in run(name)["findings"]]


assert gates("rejected_signed_lower_bound.elisa") == ["no-rule"]
assert gates("rejected_variant_exclusion.elisa") == ["non-comparison-goal"]
assert gates("rejected_qualified_body_shadow.elisa") == ["wrap-guard-goal"]

data = run("signed_lower_bound.elisa")
assert data["findings"] == [] and all("refusal_gate" not in g for g in data["goals"])
for name in ("rejected_signed_upper_bound.elisa", "rejected_variant_exclusion_ambiguous.elisa"):
    data = run(name)
    for goal in data["goals"]:
        assert ("refusal_gate" in goal) == (not goal["proven"]), goal
        assert goal.get("refusal_gate", "budget") in GATES, goal
print("refusal gate: unproven goals name their first refusing guard; proven goals carry none")
