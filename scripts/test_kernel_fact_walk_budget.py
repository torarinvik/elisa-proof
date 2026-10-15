"""Require recursive fact walkers to meter inspected node text."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def body(path: str, name: str) -> str:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\s*def {re.escape(name)}\b", line))
    indent = len(lines[start]) - len(lines[start].lstrip())
    result = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        result.append(line)
    return "\n".join(result)


walkers = (
    ("src/proof/kernel_replay/signed_fact_projection.elisa", "proof_kernel_replay_fact_contains_signed_with_work"),
    ("src/proof/kernel_replay/fact_model_integrated_helpers.elisa", "proof_kernel_replay_fact_contains_negated"),
)
for path, name in walkers:
    source = body(path, name)
    validity = source.index("not proof_kernel_replay_valid(nodes, root)")
    text_charge = source.index("proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)")
    node_read = source.index("nodes[root]")
    assert validity < text_charge < node_read, name
    assert "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in source[:node_read], name

summary = body(
    "src/proof/kernel_replay/fact_model_integrated_helpers.elisa",
    "proof_kernel_replay_fact_proves_call_summary_with_work",
)
goal_check = summary.index("proof_kernel_replay_valid(nodes, goal_root)")
goal_text = summary.index("proof_kernel_replay_goal_search_charge_node_text(nodes, goal_root, work_used)")
goal_read = summary.index("nodes[goal_root]")
assert goal_check < goal_text < goal_read
summary_check = summary.index("proof_kernel_replay_valid(nodes, summary_root)")
summary_text = summary.index("proof_kernel_replay_goal_search_charge_node_text(nodes, summary_root, work_used)")
summary_read = summary.index("proof_kernel_replay_node_at(nodes, summary_root)")
assert summary_check < summary_text < summary_read
for root in ("summary.left", "summary.right"):
    assert f"proof_kernel_replay_goal_search_charge_node_text(nodes, {root}, work_used)" in summary

reduction = body("src/proof/kernel_replay/quantifier_fact_reduction.elisa", "proof_kernel_replay_reduce_quantifier_facts_with_work")
assert "fact >= nodes.count" in reduction
assert "not proof_kernel_replay_valid(nodes, fact)" in reduction
assert reduction.index("proof_kernel_replay_goal_search_charge_node_text(nodes, fact, work_used)") < reduction.index('nodes[fact].kind == "quantifier"')
assert "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in reduction

print("kernel fact walkers: recursive node text shares the goal-search budget")
