"""Premises over sums of call results, and negated guards under a successor bound, replay."""
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


positive = report("call_sum_premise_probe.elisa", 0)
assert positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["trust"]["trusted_assumptions"] == [], positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in positive["goals"]), positive
# The capped upper bound rests on the negated guard over the two call results.
assert any(goal["name"] == "capped_pair"
           and len({origin["line"] for origin in goal["fact_origins"]
                    if origin["kind"] == "function-summary" and origin["dependency"] == "bounded_size"}) >= 2
           for goal in positive["goals"]), "capped_pair lost a call summary"
assert {goal["name"] for goal in positive["goals"]} >= {"capped_pair", "left_heavy", "plain_capped"}, positive

refused("rejected_call_sum_premise_unbounded.elisa", 12)
refused("rejected_call_sum_premise_wrong_bound.elisa", 12)
refused("rejected_negated_strict_shift_off_by_one.elisa", 7)

print("call-sum premises: generalized call results and negated successor guards replay; unbounded, tighter, and off-by-one controls refused")
