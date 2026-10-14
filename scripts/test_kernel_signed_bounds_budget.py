#!/usr/bin/env python3
"""Keep signed type-bound extraction in the caller's kernel work budget."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "src/proof/kernel_replay/division_facts.elisa"


def body(name: str) -> str:
    lines = source.read_text(encoding="utf-8").splitlines()
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
    raise AssertionError(f"missing {name}")


marker = body("proof_kernel_replay_signed_marker_info_with_goal_work")
for required in (
    "proof_kernel_replay_goal_search_charge(work_used)",
    '"__elisa_signed_type_bound"',
    "proof_kernel_replay_goal_search_charge_node_text",
    "proof_kernel_replay_constant_int_with_goal_work",
    "proof_kernel_signed_width_valid(width.value)",
    "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT",
):
    assert required in marker, required

add_bounds = body("proof_kernel_replay_add_signed_type_bounds_with_goal_work")
assert "proof_kernel_replay_signed_marker_info_with_goal_work(nodes, children, fact, 0, work_used)" in add_bounds
assert "proof_kernel_replay_add_lower_with_work(bounds, marker_name" in add_bounds
assert "proof_kernel_replay_add_upper_with_work(bounds, marker_name" in add_bounds
assert "PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in add_bounds

print("kernel signed bounds: marker parsing and bound insertion share the caller work budget")
