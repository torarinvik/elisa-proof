"""A premise with the goal as an alternative is split first, and a call rewritten by a summary keeps its original form when only that form appears in the facts."""
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


def proved(fixture, names):
    positive = report(fixture, 0)
    assert positive["status"] == "proved", positive
    assert positive["summary"]["semantic_errors"] == 0, positive
    assert positive["trust"]["trusted_assumptions"] == [], positive
    assert positive["replay"]["gaps"] == 0, positive
    assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
    assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in positive["goals"]), positive
    assert {goal["name"] for goal in positive["goals"]} >= names, positive


def refused(fixture, line):
    rejected = report(fixture, 1)
    assert rejected["status"] == "failed", rejected
    assert rejected["summary"]["semantic_errors"] == 0, rejected
    assert rejected["replay"]["gaps"] == 0, rejected
    assert ("ensure-unproven", line) in [(finding["kind"], finding["line"]) for finding in rejected["findings"]], rejected


proved("goal_disjunct_split_probe.elisa", {"a", "b"})
proved("summary_alias_probe.elisa", {"forward"})
refused("rejected_goal_disjunct_split_low_clamp.elisa", 22)
refused("rejected_summary_alias_strict.elisa", 31)

print("goal disjunct split and summary alias: probes prove and replay; low-clamp and strict-bound controls refused")
