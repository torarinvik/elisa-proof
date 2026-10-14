#!/usr/bin/env python3
"""Check the near_miss explanation on every unproven goal of the rejected examples (BACKLOG H-03)."""
import json
import os, qualified_test_binary
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_cache import json_runs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

BINARY = Path(qualified_test_binary.proof_test_binary(ROOT))


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
    examples = sorted((ROOT / "examples").glob("rejected*.elisa"))
    for example, (_, stdout) in zip(examples, json_runs(examples, BINARY)):
        try:
            report = json.loads(stdout)
        except json.JSONDecodeError:
            continue
        goals = report.get("goals", [])
        for entry in report.get("repair_queue", []):
            near = entry.get("near_miss")
            assert near is not None, f"{example.name}: goal {entry['goal_id']} has no near_miss"
            assert all(key in near for key in ("goal_names", "relevant_facts", "missing_fact", "linear_rows")), (
                f"{example.name}: goal {entry['goal_id']} has an unstable near_miss shape"
            )
            goal = goals[entry["goal_id"]]
            facts = goal["facts"]
            if near.get("goal_names_complete", False):
                assert near["missing_fact"] == goal["goal"], f"{example.name}: missing_fact is not the goal"
                goal_names = set(near["goal_names"])
                assert goal_names <= names(goal["goal"], set()), f"{example.name}: invented goal name"
            if near.get("relevant_facts_complete", False):
                goal_names = set(near["goal_names"])
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
