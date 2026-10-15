"""Lock read-before-charge fixes in bounded-model replay helpers."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/kernel_replay/goal_metered_bounded_model.elisa").read_text(encoding="utf-8")


def body(name: str) -> str:
    lines = source.splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\s*def {re.escape(name)}\b", line))
    indent = len(lines[start]) - len(lines[start].lstrip())
    result = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        result.append(line)
    return "\n".join(result)


pinned = body("proof_kernel_replay_cached_pinned_constant_with_goal_work")
assert pinned.index("proof_kernel_replay_valid(nodes, root)") < pinned.index("proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)")
assert pinned.index("proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)") < pinned.index('nodes[root].kind != "scope"')
assert "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in pinned

print("bounded-model kernel helper: root text is charged before kind inspection")
