#!/usr/bin/env python3
"""Check the near_miss explanation on every unproven goal of the rejected examples (BACKLOG H-03)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / "build/elisa-proof"


def names(expr, out):
    if isinstance(expr, dict):
        if expr.get("kind") == "ident":
            out.add(expr.get("name"))
        for value in expr.values():
            names(value, out)
    elif isinstance(expr, list):
        for value in expr:
            names(value, out)
    return out


def main():
    checked = 0
    for example in sorted((ROOT / "examples").glob("rejected*.elisa")):
        run = subprocess.run([str(BINARY), "--json", str(example)], capture_output=True, text=True, timeout=600)
        try:
            report = json.loads(run.stdout)
        except json.JSONDecodeError:
            continue
        goals = report.get("goals", [])
        for entry in report.get("repair_queue", []):
            near = entry.get("near_miss")
            assert near is not None, f"{example.name}: goal {entry['goal_id']} has no near_miss"
            goal = goals[entry["goal_id"]]
            assert near["missing_fact"] == goal["goal"], f"{example.name}: missing_fact is not the goal"
            goal_names = set(near["goal_names"])
            assert goal_names <= names(goal["goal"], set()), f"{example.name}: invented goal name"
            facts = goal["facts"]
            relevant = near["relevant_facts"]
            assert relevant == sorted(set(relevant)), f"{example.name}: relevant facts not ordered"
            for index in relevant:
                assert 0 <= index < len(facts), f"{example.name}: fact index {index} out of range"
            for index, fact in enumerate(facts):
                if index not in relevant and fact.get("kind") in ("binary", "ident", "unary", "paren"):
                    assert not (names(fact, set()) & goal_names), f"{example.name}: fact {index} shares a name but is omitted"
            checked += 1
    assert checked > 0, "no unproven goals checked"
    print(f"near_miss: {checked} unproven goals explained")


if __name__ == "__main__":
    main()
