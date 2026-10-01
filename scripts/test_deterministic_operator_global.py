"""Unverified calls and overloaded operators must not preserve stale call-site facts."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/rejected_deterministic_operator_global.elisa"

result = subprocess.run([str(BINARY), "--json", str(SOURCE)], capture_output=True, text=True, timeout=120)
assert result.returncode == 1, result.stderr
report = json.loads(result.stdout)
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"]

declarations = {item["name"]: item for item in report["declaration_details"] if item["kind"] == "function"}
assert declarations["hidden_index_mutator"]["verified"] is False, declarations["hidden_index_mutator"]
assert declarations["rejected_shortcircuit_index"]["verified"] is False, declarations["rejected_shortcircuit_index"]
assert declarations["rejected_direct_overload_index"]["verified"] is False, declarations["rejected_direct_overload_index"]
assert declarations["rejected_nested_shortcircuit_operator_index"]["verified"] is False, declarations["rejected_nested_shortcircuit_operator_index"]
assert declarations["rejected_operator_assert_index"]["verified"] is False, declarations["rejected_operator_assert_index"]
assert declarations["rejected_operator_match_guard_index"]["verified"] is False, declarations["rejected_operator_match_guard_index"]
assert declarations["rejected_value_match_operator_guard"]["verified"] is False, declarations["rejected_value_match_operator_guard"]
assert declarations["rejected_value_match_operator_scrutinee"]["verified"] is False, declarations["rejected_value_match_operator_scrutinee"]
assert declarations["rejected_operator_loop_index"]["verified"] is False, declarations["rejected_operator_loop_index"]
assert declarations["rejected_operator_expression_statement"]["verified"] is False, declarations["rejected_operator_expression_statement"]
assert declarations["rejected_operator_initializer_effect"]["verified"] is False, declarations["rejected_operator_initializer_effect"]
assert declarations["rejected_operator_assignment_effect"]["verified"] is False, declarations["rejected_operator_assignment_effect"]
assert declarations["rejected_operator_return_effect"]["verified"] is False, declarations["rejected_operator_return_effect"]
assert declarations["rejected_operator_branch_body_index"]["verified"] is False, declarations["rejected_operator_branch_body_index"]

# Both signed index obligations need to remain open after the RHS can mutate the global index.
for function_name in (
    "rejected_shortcircuit_index",
    "rejected_direct_overload_index",
    "rejected_nested_shortcircuit_operator_index",
    "rejected_operator_assert_index",
    "rejected_operator_loop_index",
    "rejected_operator_expression_statement",
    "rejected_operator_initializer_effect",
    "rejected_operator_assignment_effect",
    "rejected_operator_return_effect",
    "rejected_operator_branch_body_index",
):
    index_goals = [goal for goal in report["goals"] if goal["name"] == function_name and goal["rule"].startswith("index-")]
    assert {goal["rule"] for goal in index_goals} == {"index-lower", "index-upper"}, index_goals
    assert all(not goal["proven"] and goal["replay_status"] == "not_certified" for goal in index_goals), index_goals
for function_name in (
    "rejected_operator_match_guard_index",
    "rejected_value_match_operator_guard",
    "rejected_value_match_operator_scrutinee",
):
    match_goals = [goal for goal in report["goals"] if goal["name"] == function_name and goal["rule"] != "resource-safety"]
    assert match_goals and all(not goal["proven"] and goal["replay_status"] == "not_certified" for goal in match_goals), match_goals
assert any(finding["kind"] == "function-summary-unverified" and finding["name"] == "rejected_shortcircuit_index" for finding in report["findings"]), report["findings"]

# Custom-type operators are rejected by the type-aware statement-admission path even when there
# is no primitive operator implementation to set the source-operator mask.
custom_source = ROOT / "examples/rejected_custom_operator_global.elisa"
custom_result = subprocess.run([str(BINARY), "--json", str(custom_source)], capture_output=True, text=True, timeout=120)
assert custom_result.returncode == 1, custom_result.stderr
custom_report = json.loads(custom_result.stdout)
assert custom_report["summary"]["semantic_errors"] == 0, custom_report["semantic_diagnostics"]
assert custom_report["replay"]["gaps"] == 0, custom_report["replay"]
assert custom_report["replay"]["certificates"] == custom_report["replay"]["replayed"]
custom_declarations = {item["name"]: item for item in custom_report["declaration_details"] if item["kind"] == "function"}
for function_name in ("rejected_custom_operator_index", "rejected_custom_match_guard_index"):
    assert custom_declarations[function_name]["verified"] is False, custom_declarations[function_name]
    assert not any(goal["name"] == function_name and goal["rule"].startswith("index-") and goal["proven"] for goal in custom_report["goals"]), custom_report["goals"]
    assert any(finding["kind"] == "expression-unsupported" and finding["name"] == function_name and "unmodeled user protocol" in finding["message"] for finding in custom_report["findings"]), custom_report["findings"]

print("unverified calls and overloaded operators cannot carry stale index facts across branches")
