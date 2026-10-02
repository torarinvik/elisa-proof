"""Check conditional result transport, aliases, and strict-order rejection controls."""
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
run = subprocess.run([binary, "--json", str(root / "examples/call_result_order_transport_gap.elisa")],
                     capture_output=True, text=True, timeout=30)
assert run.returncode == 1, run.stderr
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
assert report["replay"]["replayed"] == report["replay"]["certificates"]
assert not report["trust"]["trusted_assumptions"]
assert {f["name"] for f in report["findings"]} == {
    "rejected_nonstrict_nonzero_call_result", "rejected_mutated_conditional_result",
    "rejected_zero_constant_conditional_result", "rejected_invalid_conditional_nonzero_result",
    "rejected_true_guard_nonzero_result"}
for name in ("automatic_nonzero_call_result", "checked_nonzero_call_result",
             "automatic_conditional_nonzero_result", "automatic_fixed_valid_nonzero_result",
             "automatic_reverse_order_conditional_result", "automatic_captured_conditional_result"):
    assert any(d.get("name") == name and d.get("verified") for d in report["declaration_details"])
print("Conditional summaries, reversed order, and captured aliases replay; false and mutated controls reject")
