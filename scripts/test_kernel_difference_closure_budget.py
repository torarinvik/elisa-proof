#!/usr/bin/env python3
"""Keep unsigned plain-bound propagation inside the shared goal-search budget."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            end = index + 1
            while end < len(lines):
                following = lines[end]
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[index:end])
    raise AssertionError(f"missing {name} in {path}")


guarded = ROOT / "src/proof/kernel_replay/guarded_differences.elisa"
goal_difference = ROOT / "src/proof/kernel_replay/goal_metered_difference.elisa"
plain_closure = body(guarded, "proof_kernel_replay_close_plain_bounds_with_goal_work")
assert "-> bool:" in plain_closure.splitlines()[0]
assert "proof_kernel_replay_goal_search_charge(goal_work)" in plain_closure
assert "proof_kernel_replay_difference_bound_closure_with_work(constraints, bounds, goal_work)" in plain_closure
assert "proof_kernel_replay_close_bounds_through_differences" not in plain_closure
assert "goal_work <- PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT + 1" in plain_closure
assert "return false" in plain_closure and "return true" in plain_closure
guarded_source = guarded.read_text(encoding="utf-8")
assert not re.search(r"\bdef\s+proof_kernel_replay_close_plain_bounds\b", guarded_source)
collector = body(guarded, "proof_kernel_replay_collect_plain_differences")
for required in (
    "proof_kernel_replay_primitive_comparison_with_markers_with_work",
    "proof_kernel_replay_guarded_difference_import_with_work",
    "proof_kernel_replay_plain_order_side_with_goal_work",
    "proof_kernel_replay_collect_differences_with_goal_work",
):
    assert required in collector, required
for legacy in (
    "proof_kernel_replay_primitive_comparison(",
    "proof_kernel_replay_primitive_comparison_with_work(",
    "proof_kernel_replay_guarded_difference_import(",
    "proof_kernel_replay_collect_differences(",
):
    assert legacy not in collector, legacy

plain_side = body(guarded, "proof_kernel_replay_plain_order_side_with_goal_work")
assert "proof_kernel_replay_goal_search_charge(goal_work)" in plain_side
assert "root >= nodes.count" in plain_side

for path, caller in (
    (guarded, "proof_kernel_replay_unsigned_safe_closing_with_goal_work"),
    (ROOT / "src/proof/kernel_replay/unsigned_bounds.elisa", "proof_kernel_replay_unsigned_expression_safe_with_replay_work"),
    (ROOT / "src/proof/kernel_replay/unsigned_bounds.elisa", "proof_kernel_replay_unsigned_report_safe_with_goal_work"),
):
    caller_body = body(path, caller)
    assert "return false if not proof_kernel_replay_close_plain_bounds_with_goal_work" in caller_body, caller

unsigned_bounds = (ROOT / "src/proof/kernel_replay/unsigned_bounds.elisa").read_text(encoding="utf-8")
assert not re.search(r"\bdef\s+proof_kernel_replay_unsigned_facts_safe\b", unsigned_bounds)
assert not re.search(r"\bdef\s+proof_kernel_replay_unsigned_goal_safe\b", unsigned_bounds)
assert not re.search(r"\bdef\s+proof_kernel_replay_unsigned_expression_safe\b", unsigned_bounds)

metered_closure = body(goal_difference, "proof_kernel_replay_difference_bound_closure_with_work")
assert metered_closure.index("return false if work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT") < metered_closure.index("return true if constraints.count == 0")
for required in (
    "proof_kernel_replay_equality_vertex_index_build",
    "proof_kernel_replay_equality_vertex_index_insert",
    "proof_kernel_replay_equality_vertex_index_find",
    "proof_kernel_replay_goal_search_charge(work_used)",
    "proof_kernel_replay_difference_add_upper_at_vertex_with_work",
    "proof_kernel_replay_difference_add_lower_at_vertex_with_work",
    "PROOF_KERNEL_REPLAY_BOUND_PROPAGATION_ROUND_LIMIT",
):
    assert required in metered_closure, required

print("kernel difference closure: unsigned fixed-point propagation shares the goal budget and refuses exhaustion")
