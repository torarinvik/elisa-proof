#!/usr/bin/env python3
"""Focused CLI coverage for indexed apply transitions and replay."""

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "build" / "elisa-proof"


def ident(name):
    return {"kind": "ident", "name": name}


def implication(left, right):
    return {
        "kind": "binary",
        "operator": "=>",
        "left": left,
        "right": right,
    }


def run_script(document, source):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as script:
        json.dump(document, script)
        script.flush()
        return subprocess.run(
            [str(BINARY), "--tactics", script.name, str(source)],
            check=False,
            capture_output=True,
            text=True,
        )


def result_for(document, source):
    process = run_script(document, source)
    return process, json.loads(process.stdout)


portable_source = ROOT / "examples" / "verified.elisa"
goal = ident("Q")
premise_a = ident("A")
premise_b = ident("B")
initial = {
    "facts": [implication(premise_a, goal), implication(premise_b, goal), premise_b],
    "goal": goal,
}

# The first implication would leave the unprovable premise A. An explicit index must select
# the second implication, after which B is already an exact hypothesis.
selected = {
    "format": "elisa-proof-tactics-v1",
    "initial": initial,
    "actions": [
        {"action": "apply", "argument_index": 1},
        {"action": "assumption"},
    ],
}
process, report = result_for(selected, portable_source)
assert process.returncode == 0, (process.returncode, process.stderr, report)
assert report["status"] == "proved" and report["tactic"]["solved"]
assert report["tactic"]["trace_replayed"]
assert report["tactic"]["kernel_trace_replayed"]
assert report["tactic"]["certificate_replayed"]
apply_step = report["state"]["trace"][0]
assert apply_step["action"] == "apply" and apply_step["accepted"]
assert apply_step["has_argument_index"] and apply_step["argument_index"] == 1
assert apply_step["has_argument"] is False and apply_step["has_secondary"] is False
assert apply_step["goal"] == ident("B")

# A well-formed but out-of-range index remains a recorded rejected no-op. Both trace replayers
# must accept that refusal, while the final result stays open and cannot receive a certificate.
rejected = {
    "format": "elisa-proof-tactics-v1",
    "initial": initial,
    "actions": [{"action": "apply", "argument_index": 99, "accepted": False}],
}
process, report = result_for(rejected, portable_source)
assert process.returncode == 1, (process.returncode, process.stderr, report)
assert report["tactic"]["valid"] and not report["tactic"]["solved"]
assert report["tactic"]["trace_replayed"]
assert report["tactic"]["kernel_trace_replayed"]
assert not report["tactic"]["certificate_replayed"]
rejected_step = report["state"]["trace"][0]
assert rejected_step["action"] == "apply" and not rejected_step["accepted"]
assert rejected_step["has_argument_index"] and rejected_step["argument_index"] == 99
assert report["state"]["facts"] == report["state"]["initial_facts"]
assert report["state"]["goal"] == report["state"]["initial_goal"]

# Exercise the same indexed refusal through source-bound goal selection. An invalid fact index
# must not detach the script from the imported goal or bypass the source/kernel replay gates.
source_bound = {
    "format": "elisa-proof-tactics-v1",
    "target": {"goal_id": 1, "goal_fingerprint": 2903951783},
    "actions": [{"action": "apply", "argument_index": 999, "accepted": False}],
}
process, report = result_for(source_bound, ROOT / "examples" / "tactic_repair_target.elisa")
assert process.returncode == 1, (process.returncode, process.stderr, report)
assert report["source_goal_binding"]["bound"]
assert report["source_goal_binding"]["goal_id"] == 1
assert report["source_goal_binding"]["fingerprint_match"]
assert report["tactic"]["valid"] and not report["tactic"]["solved"]
assert report["tactic"]["trace_replayed"]
assert report["tactic"]["kernel_trace_replayed"]
source_step = report["state"]["trace"][0]
assert source_step["action"] == "apply" and not source_step["accepted"]
assert source_step["has_argument_index"] and source_step["argument_index"] == 999

print("indexed apply: selected context facts and rejected indexes replay through both tactic paths")
