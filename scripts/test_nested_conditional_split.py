"""A conditional nested inside a comparison splits on its condition, rewriting goal and facts."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(fixture, expected_status):
    run = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / fixture)],
        capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == expected_status, (fixture, run.returncode, run.stderr)
    return json.loads(run.stdout)


def refused(fixture, line):
    rejected = report(fixture, 1)
    assert rejected["status"] == "failed", rejected
    assert rejected["summary"]["semantic_errors"] == 0, rejected
    assert rejected["trust"]["trusted_assumptions"] == [], rejected
    assert [(finding["kind"], finding["line"]) for finding in rejected["findings"]] == [("ensure-unproven", line)], rejected
    assert rejected["replay"]["gaps"] == 0, rejected
    return rejected


positive = report("nested_conditional_split_probe.elisa", 0)
assert positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["trust"]["trusted_assumptions"] == [], positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in positive["goals"]), positive
assert {goal["name"] for goal in positive["goals"]} >= {"tree_height", "successor_of_max", "min_plus_max_is_sum"}, positive
# The recursive height bound rests on both recursive calls' own summaries.
assert any(goal["name"] == "tree_height" and goal["line"] == 21
           and len({origin["line"] for origin in goal["fact_origins"]
                    if origin and origin["kind"] == "function-summary" and origin["dependency"] == "tree_height"}) >= 2
           for goal in positive["goals"]), "tree_height lost a recursive summary"

refused("rejected_nested_conditional_unguarded.elisa", 7)
refused("rejected_nested_conditional_wrong_branch.elisa", 7)
refused("rejected_nested_conditional_max_twice.elisa", 6)

print("nested conditionals: split with goal and facts rewritten per branch replays; unguarded, wrong-branch, and max-twice controls refused")
