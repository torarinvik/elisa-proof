"""Guard the central kernel expression-equality walk's bounds and work ordering."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/kernel_replay/difference_constraints.elisa").read_text(encoding="utf-8")


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


equal = body("proof_kernel_replay_expr_equal_with_work")
assert equal.index("not proof_kernel_replay_valid(nodes, left_root)") < equal.index("pending: mutable")
assert equal.index("not proof_kernel_replay_expr_equality_work_charge(1") < equal.index("pending: mutable")
pair_loop = equal.split("while pending.count > 0", 1)[1]
for gate in ("pair.left >= nodes.count", "pair.right >= nodes.count"):
    assert gate in pair_loop
for node in ("nodes[pair.left]", "nodes[pair.right]"):
    assert pair_loop.index("proof_kernel_replay_expr_equality_node_work(" + node) < pair_loop.index("proof_kernel_replay_expr_pair_expand(")
assert "PROOF_KERNEL_REPLAY_MAX_EXPR_EQUALITY_PENDING" not in equal  # queue cap is enforced before allocation

enqueue = body("proof_kernel_replay_expr_pair_enqueue")
assert "scheduled >= PROOF_KERNEL_REPLAY_MAX_EXPR_EQUALITY_WORK" in enqueue
assert "pending.count >= PROOF_KERNEL_REPLAY_MAX_EXPR_EQUALITY_PENDING" in enqueue
assert enqueue.index("pending.count >= PROOF_KERNEL_REPLAY_MAX_EXPR_EQUALITY_PENDING") < enqueue.index("pending.push(")

charge = body("proof_kernel_replay_expr_equality_node_work")
for field in ("kind", "name", "secondary_name", "operator"):
    assert f"sview_len(node.{field})" in charge

leaf = body("proof_kernel_replay_expr_leaf_equal")
for field in ("kind", "left_name", "right_name"):
    assert f"sview_len({field})" in leaf
assert "(complete: bool, handled: bool, equal: bool)" in source
expand = body("proof_kernel_replay_expr_pair_expand")
assert expand.index("if not leaf.complete") < expand.index("if leaf.handled") < expand.index("proof_kernel_replay_expr_pair_enqueue_children")

print("kernel expression equality: roots, node text, and pending work are bounded before use")
