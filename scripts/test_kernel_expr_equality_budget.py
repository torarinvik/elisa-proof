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

children = body("proof_kernel_replay_expr_pair_enqueue_children")
checked_index_equality_branch = children.split('"binary" | "index" | "dict_entry" | "checked-index":', 1)[1].split(
    '"slice" | "if":', 1
)[0]
assert "return proof_kernel_replay_expr_pair_enqueue_two(" in checked_index_equality_branch
assert '"checked-get"' not in children

fact_index = (ROOT / "src/proof/replay/kernel_fact_root_index.elisa").read_text(encoding="utf-8")
index_dimensions = fact_index.split("def proof_replay_kernel_fact_root_index_dimensions_match(", 1)[1].split(
    "\n\n        def", 1
    )[0]
for identity in (
    "index.report_identity == (&report).cast[uintptr]",
    "index.trace_count == report.analysis_1.traces.records.count",
    "index.kernel_node_count == report.analysis_1.kernel.nodes.count",
    "index.kernel_child_count == report.analysis_1.kernel.children.count",
):
    assert identity in index_dimensions
index_ensure = fact_index.split("def proof_replay_kernel_fact_root_index_ensure(", 1)[1].split(
    "\n\n        def", 1
)[0]
assert "index.attempted and proof_replay_kernel_fact_root_index_dimensions_match(report, index)" in index_ensure
assert index_ensure.index("proof_replay_kernel_fact_root_index_reset(index)") < index_ensure.index("index.report_identity <-") < index_ensure.index("proof_replay_kernel_fact_root_index_build(report, index)")
index_find = fact_index.split("def proof_replay_kernel_fact_root_index_find(", 1)[1].split(
    "\n\n        def", 1
)[0]
assert "not proof_replay_kernel_fact_root_index_dimensions_match(report, index)" in index_find
replay_api = (ROOT / "src/proof/replay/api.elisa").read_text(encoding="utf-8")
for entry_name in ("proof_replay_fact_trace_entry_with_cache", "proof_replay_certificates_mutating"):
    entry = replay_api.split(f"def {entry_name}", 1)[1].split("\n\n        def", 1)[0]
    assert "structural_cache: mutable ProofReplayStructuralValidationCache = ProofReplayStructuralValidationCache{}" in entry
root_hash = fact_index.split("def proof_replay_kernel_fact_root_hash_node(", 1)[1].split(
    "def proof_replay_kernel_fact_root_index_reset(", 1
)[0]
checked_index_hash_branch = root_hash.split('node.kind in {"binary", "index", "dict_entry", "checked-index"}', 1)[1].split(
    'elif node.kind == "slice"', 1
)[0]
assert "children, node.left" in checked_index_hash_branch
assert "children, node.right" in checked_index_hash_branch
assert '"checked-get"' not in root_hash

runtime = (ROOT / "examples/kernel_interval_contradiction_runtime.elisa").read_text(encoding="utf-8")
assert 'add_node(&nodes, "checked-index", "", index_term, one,' in runtime
assert 'add_node(&nodes, "checked-index", "", index_term, zero,' in runtime
assert 'add_node(&nodes, "checked-index", "", other_index_term, one,' in runtime
assert 'return 35 if not proof_kernel_replay_expr_equal_public(&nodes, &children, checked_index, checked_index_copy, 0)' in runtime
assert 'return 36 if proof_kernel_replay_expr_equal_public(&nodes, &children, checked_index, checked_index_other_fallback, 0)' in runtime
assert 'return 40 if proof_kernel_replay_expr_equal_public(&nodes, &children, checked_index, checked_index_other_guard, 0)' in runtime
assert 'return 37 if proof_kernel_replay_expr_equal_public(&nodes, &children, checked_get, checked_get, 0)' in runtime
assert 'return 41 if proof_kernel_replay_expr_equal_public(&nodes, &children, malformed_checked_index_shape, malformed_checked_index_shape, 0)' in runtime
assert 'return 38 if proof_kernel_replay_expr_equal_public(&nodes, &children, bad_checked_index, bad_checked_index, 0)' in runtime
assert 'return 39 if proof_kernel_replay_expr_equal_public(&nodes, &children, checked_index_cycle, checked_index_cycle, 0)' in runtime

arena_shapes = (ROOT / "src/proof/kernel_replay/arena_shapes.elisa").read_text(encoding="utf-8")
checked_index_shape = arena_shapes.split('if node.kind == "checked-index":', 1)[1].split(
    'if node.kind == "checked-get":', 1
)[0]
assert "node.auxiliary == 0" in checked_index_shape
assert "node.children_start == 0" in checked_index_shape and "node.children_count == 0" in checked_index_shape

print("kernel expression equality: roots, node text, and pending work are bounded before use")
