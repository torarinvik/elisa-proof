#!/usr/bin/env python3
"""Keep disjunction literal decoding on the shared replay work meter."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/kernel_replay/relevant_disjunctions.elisa").read_text(encoding="utf-8")

for legacy in (
    "proof_kernel_replay_disjunct_literal_bool(",
    "proof_kernel_replay_disjunct_small_literal_value(",
):
    assert legacy not in source, legacy

assert "def proof_kernel_replay_disjunct_literal_bool_with_work" in source
assert "def proof_kernel_replay_disjunct_small_literal_value_with_work" in source
assert "proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)" in source
