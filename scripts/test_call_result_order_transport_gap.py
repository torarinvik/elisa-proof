"""Check named conditional-summary transport and adversarial mapping controls."""
import json
import os
from collections import Counter
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
assert report["replay"]["certificates"] > 0
assert report["replay"]["replayed"] == report["replay"]["certificates"]
assert not report["trust"]["trusted_assumptions"]
assert {f["name"] for f in report["findings"]} == {
    "rejected_nonstrict_nonzero_call_result", "rejected_mutated_conditional_result",
    "rejected_zero_constant_conditional_result", "rejected_invalid_conditional_nonzero_result",
    "rejected_true_guard_nonzero_result", "rejected_named_swapped_same_typed",
    "altered_named_conditional_summary", "rejected_named_false_summary",
    "rejected_named_guard_write"}
altered_findings = [finding for finding in report["findings"]
                    if finding["name"] == "altered_named_conditional_summary"]
assert Counter((finding["kind"], finding["status"]) for finding in altered_findings) == Counter({
    ("ensure-unproven", "disproved"): 2}), altered_findings
false_summary_findings = [finding for finding in report["findings"]
                          if finding["name"] == "rejected_named_false_summary"]
assert Counter((finding["kind"], finding["status"]) for finding in false_summary_findings) == Counter({
    ("function-summary-unverified", "unsupported"): 1,
    ("ensure-unproven", "unknown"): 1}), false_summary_findings
for name in ("automatic_nonzero_call_result", "checked_nonzero_call_result",
             "automatic_conditional_nonzero_result", "automatic_fixed_valid_nonzero_result",
             "automatic_reverse_order_conditional_result", "automatic_captured_conditional_result",
             "automatic_named_conditional_result", "automatic_named_shadowed_names"):
    assert any(d.get("name") == name and d.get("verified") for d in report["declaration_details"])


def summary_trace(owner: str) -> dict:
    return next(trace for trace in report["kernel"]["fact_traces"]
                if trace["kind"] == "function-summary" and
                trace["dependency"] == "named_conditional_pair_result" and
                trace["name"] == owner and trace["summary_ensure_index"] == 0)


def assert_named_call_mapping(owner: str, expected_bindings: dict[str, str],
                              expected_arguments: list[str]) -> None:
    trace = summary_trace(owner)
    bindings = {entry["parameter"]: entry["value"] for entry in trace["summary_bindings"]}
    for parameter, actual in expected_bindings.items():
        assert bindings[parameter]["kind"] == "ident" and bindings[parameter]["name"] == actual, bindings
    call = bindings["result"]
    assert call["kind"] == "call" and call["argument_names"] == ["right", "left", "valid"], call
    assert [argument.get("name") for argument in call["arguments"]] == expected_arguments, call
    # The verified caller's postcondition must consume this source-derived summary, not just emit
    # an unused trace whose counters happen to report a clean replay.
    assert any(goal["name"] == owner and goal["proven"] and
               any(dependency["kind"] == "function-summary" and
                   dependency["name"] == "named_conditional_pair_result"
                   for dependency in goal["dependencies"])
               for goal in report["goals"]), owner


assert_named_call_mapping("automatic_named_conditional_result",
                          {"valid": "valid", "left": "left", "right": "right"},
                          ["right", "left", "valid"])
assert_named_call_mapping("automatic_named_shadowed_names",
                          {"valid": "valid", "left": "right", "right": "left"},
                          ["left", "right", "valid"])

functions = {entry["name"]: entry for entry in report["declaration_details"]
             if entry.get("kind") == "function"}
assert not functions["altered_named_conditional_summary"]["verified"]
assert not functions["rejected_named_false_summary"]["verified"]
assert functions["rejected_named_false_summary"]["verification_reason"] == "dependency-unverified"
assert not any(trace.get("dependency") == "altered_named_conditional_summary" and
               trace.get("name") == "rejected_named_false_summary"
               for trace in report["kernel"]["fact_traces"])
# The earlier mutation control changes a captured result alias; this one changes the guard after
# the call and checks the post-state. Neither is a by-reference aliasing test: the summary's
# parameters here are all by-value scalars.
assert not functions["rejected_named_guard_write"]["verified"]
print("Named conditional summaries map and replay exactly; swapped, false, mutated, and post-write controls reject")
