"""Recursive payload-enum functions keep sibling call summaries and type scalar binders exactly."""
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
    # A goal may lean on the refused function's own summary; such a certificate is never
    # counted as replayed, and nothing else may be a gap.
    for goal in rejected["goals"]:
        if goal["replay_status"] == "gap":
            assert any(dependency["kind"] == "function-summary" for dependency in goal["dependencies"]), goal
    return rejected


positive = report("adt_recursive_payload_probe.elisa", 0)
assert positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["trust"]["trusted_assumptions"] == [], positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in positive["goals"]), positive
# Some tree_size goal holds both recursive summaries, one per subtree call.
assert any(goal["name"] == "tree_size"
           and len({origin["line"] for origin in goal["fact_origins"]
                    if origin["kind"] == "function-summary" and origin["dependency"] == "tree_size"}) >= 2
           for goal in positive["goals"]), "tree_size lost a sibling summary"

refused("rejected_adt_recursive_payload_difference.elisa", 17)
refused("rejected_adt_payload_binder_position.elisa", 13)
refused("rejected_adt_payload_binder_width.elisa", 12)

print("recursive payload enums: sibling summaries and binder types replay; difference, position, and width controls refused")
