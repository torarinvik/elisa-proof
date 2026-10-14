"""`ensures` is the plural postcondition head: checked on every return and read by callers."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

BINARY = Path(qualified_test_binary.proof_test_binary(ROOT))


def report(name, expected_status):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / f"{name}.elisa")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected_status, (name, run.returncode, run.stderr, run.stdout)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["replay"]["gaps"] == 0, data
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data
    return data


accepted = report("body_ensures", 0)
assert accepted["status"] == "proved", accepted
assert accepted["findings"] == [], accepted["findings"]
functions = {d["name"]: d for d in accepted["declaration_details"] if d.get("kind") == "function"}
for name in ("plural_on_every_return", "plural_summary", "caller_reads_plural", "both_spellings"):
    assert functions[name]["verified"], functions[name]
for name in ("implicit_result_substitution", "explicit_result_substitution", "guarded_match_result"):
    assert functions[name]["verified"], functions[name]
assert accepted["source"]["admissible"] is True, accepted["source"]
assert accepted["source"]["goal_admissions_complete"] is True, accepted["source"]
substituted_goals = [goal for goal in accepted["goals"] if goal["name"] == "implicit_result_substitution"]
assert substituted_goals and all(goal["replay_status"] == "replayed" and goal["proven"] for goal in substituted_goals), substituted_goals
explicit_substituted_goals = [goal for goal in accepted["goals"] if goal["name"] == "explicit_result_substitution"]
assert explicit_substituted_goals and all(goal["replay_status"] == "replayed" and goal["proven"] for goal in explicit_substituted_goals), explicit_substituted_goals
guarded_match_goals = [goal for goal in accepted["goals"] if goal["name"] == "guarded_match_result"]
assert guarded_match_goals and all(goal["replay_status"] == "replayed" and goal["proven"] for goal in guarded_match_goals), guarded_match_goals

rejected = report("rejected_body_ensures", 1)
assert rejected["status"] == "failed", rejected
found = sorted((f["line"], f["name"], f["kind"]) for f in rejected["findings"])
assert found == [
    (5, "plural_false", "ensure-unproven"),
    (6, "plural_false", "ensure-unproven"),
    (12, "plural_beside_true", "ensure-unproven"),
], found

wrong_guard = report("rejected_match_guard_result", 1)
assert wrong_guard["status"] == "failed", wrong_guard
assert [(finding["kind"], finding["name"]) for finding in wrong_guard["findings"]] == [
    ("ensure-unproven", "guarded_match_wrong_guard")
], wrong_guard["findings"]

void_results = report("rejected_void_result_postcondition", 1)
assert void_results["source"]["admissible"] is False, void_results["source"]
void_functions = {item["name"]: item for item in void_results["declaration_details"] if item.get("kind") == "function"}
for owner in ("direct_void_result", "aliased_void_result"):
    assert owner in void_functions and not void_functions[owner]["verified"], void_functions.get(owner)
    goals = [goal for goal in void_results["goals"] if goal["name"] == owner]
    assert goals and all(not goal["proven"] for goal in goals), goals

print("body ensures: source-bound results and payload guards replay; wrong guards and void result postconditions fail closed")
