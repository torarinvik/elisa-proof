#!/usr/bin/env python3
"""Guard shared work accounting in finite quantified-premise replay."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/kernel_replay/quantified_premises.elisa").read_text()


def function_body(name: str, next_name: str) -> str:
    start = SOURCE.index(f"def {name}(")
    end = SOURCE.index(f"def {next_name}(", start)
    return SOURCE[start:end]


candidate = function_body(
    "proof_kernel_replay_finite_predicate_goal_candidate",
    "proof_kernel_replay_finite_universal_premise",
)
finite = SOURCE[SOURCE.index("def proof_kernel_replay_finite_universal_premise("):]

assert "work_used: mutable usize&" in candidate
assert "proof_kernel_replay_goal_search_charge(work_used)" in candidate
assert candidate.count("proof_kernel_replay_goal_search_charge_node_text(nodes,") == 2
assert "proof_kernel_replay_constant_int(nodes," not in candidate
assert candidate.count("proof_kernel_replay_constant_int_with_goal_work(") == 2
assert "for offset in 0..<node.children_count" in candidate
assert "return empty if not proof_kernel_replay_goal_search_charge(work_used)" in candidate
assert "work_used: mutable usize&" in finite
assert finite.count("proof_kernel_replay_goal_search_charge_node_text(nodes,") == 2
assert finite.count("proof_kernel_replay_constant_int_with_goal_work(") >= 2
assert "proof_kernel_replay_constant_int(nodes," not in finite
assert "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in finite

print("quantifier premise replay: candidate and endpoint scans share the goal-search meter")
