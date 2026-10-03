#!/usr/bin/env python3
"""A comprehension variable is bound in a child resource scope, so its calls replay (no gaps)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_cache import json_run  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def report(name):
    _, stdout = json_run(ROOT / "examples" / f"{name}.elisa")
    return json.loads(stdout)


def resource_events(rep, function):
    nodes, children = rep["kernel"]["nodes"], rep["kernel"]["children"]
    goal = next(g for g in rep["goals"] if g["rule"] == "resource-safety" and g["name"] == function)
    seen, stack = [], [(goal["kernel_goal"], 0)]
    while stack:
        index, depth = stack.pop()
        node = nodes[index]
        seen.append((node["kind"], node["name"], depth))
        if node["kind"] in ("resource-safety", "resource-scope"):
            start = node["children_start"]
            stack.extend((child, depth + 1) for child in children[start:start + node["children_count"]])
    return goal, seen


def main():
    rep = report("comprehension_borrowed_call")
    assert rep["replay"]["gaps"] == 0, rep["replay"]
    assert rep["replay"]["certificates"] == rep["replay"]["replayed"] > 0
    for function in ("any_matches", "first_unmatched", "shadowing_variable"):
        goal, events = resource_events(rep, function)
        assert goal["proven"] and goal["replay_status"] == "replayed", (function, goal["replay_status"])
        # The variable is bound inside a scope; only a same-named parameter sits at the top level.
        variable = "xs" if function == "shadowing_variable" else "z"
        binds = [depth for kind, name, depth in events if kind == "resource-bind" and name == variable]
        assert any(depth >= 2 for depth in binds), (function, binds)
        assert binds.count(1) == (1 if function == "shadowing_variable" else 0), (function, binds)
    rejected = report("rejected_comprehension_moved_value")
    assert rejected["status"] == "failed" and rejected["replay"]["gaps"] == 0
    assert any(f["kind"] == "resource-use-after-move" and f["line"] == 7 for f in rejected["findings"]), rejected["findings"]
    print("comprehension resources: scoped variable bindings replay; a move in the condition is refused")


if __name__ == "__main__":
    main()
