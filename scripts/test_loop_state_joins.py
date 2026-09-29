"""Loop states survive rebinds, arm locals and aggregate calls; false controls stay open."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name, code):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (name + ".elisa"))],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == code, (name, run.returncode, run.stderr)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data["summary"]
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data["replay"]
    return data


accepted = report("loop_state_joins", 0)
functions = {d["name"]: d for d in accepted["declaration_details"] if d.get("kind") == "function"}
for name in ("decimal", "digit_step", "local_extent", "constant_invariant", "alias_rebind",
             "negated_order", "rebound_arms", "arm_local", "aggregate_summary"):
    assert functions[name]["verified"], (name, functions[name])
assert accepted["findings"] == [], accepted["findings"]
rejected = report("rejected_loop_state_joins", 1)
found = {(f["name"], f["kind"]) for f in rejected["findings"]}
expected = {("untrue_aggregate_bound", "ensure-unproven"), ("escaping_arm", "invariant-not-preserved"),
            ("arm_local_value", "ensure-unproven"), ("growing_arm_local", "invariant-not-preserved"),
            ("untrue_negated_order", "ensure-unproven")}
assert expected <= found, sorted(expected - found)
print("loop state joins: rebinds, arm locals, negated orders and aggregate summaries replay; false controls stay open")
