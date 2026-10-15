#!/usr/bin/env python3
"""Keep quantifier binder arity tied to the encoded range kind during arena admission."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
replay_path = ROOT / "src/proof/kernel_replay/quantifiers_and_arena.elisa"
arena_path = ROOT / "src/proof/kernel_replay/arena_child_validation.elisa"
encoder_path = ROOT / "src/proof/kernel_encode.elisa"


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


arena_children = body(arena_path, "proof_kernel_replay_arena_children_valid_with_work")
assert 'node.kind == "quantifier"' in arena_children
quantifier_shape = body(arena_path, "proof_kernel_replay_quantifier_range_arity_valid")
assert "range: ElisaProofKernelCore::ProofKernelNode = nodes[node.left]" in quantifier_shape
assert "(node.auxiliary == 1 and range.kind != \"dict\") or (node.auxiliary == 2 and range.kind == \"dict\")" in quantifier_shape
assert "proof_kernel_replay_arena_shape_text_work_charge(sview_len(range.kind), &work_used, range_kind_work_before, work_limit)" in arena_children
assert "proof_kernel_replay_quantifier_range_arity_valid(nodes, node)" in arena_children

safe_constant = body(replay_path, "proof_kernel_replay_quantifier_safe_comparison_constant_with_work")
assert "proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)" in safe_constant
assert "proof_kernel_replay_arena_scalar_shape(root_node)" in safe_constant
assert "root_node.kind == \"int\" and shape.known and shape.valid and root_node.value >= 0" in safe_constant
assert "proof_kernel_replay_quantifier_charge_work(work_used, 1)" not in safe_constant

small_signed = body(replay_path, "proof_kernel_quantifier_small_signed_bound_with_work")
assert "proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)" in small_signed
assert "proof_kernel_replay_goal_search_charge_node_text(nodes, operand, work_used)" in small_signed
assert "proof_kernel_replay_arena_general_shape_valid(root_node)" in small_signed
assert "proof_kernel_replay_arena_scalar_shape(operand_node)" in small_signed
assert "proof_kernel_quantifier_small_signed_bound(nodes, root)" not in small_signed

exact_bound = body(replay_path, "proof_kernel_replay_quantifier_exact_int_from_bounds")
assert "proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)" in exact_bound
assert "proof_kernel_replay_arena_shape_valid(root_node)" in exact_bound
assert exact_bound.index("proof_kernel_replay_goal_search_charge_node_text(nodes, root, work_used)") < exact_bound.index("root_node: ElisaProofKernelCore::ProofKernelNode = nodes[root]")
assert exact_bound.index("proof_kernel_replay_arena_shape_valid(root_node)") < exact_bound.index("proof_kernel_replay_bound_for_with_work(bounds, root_node.name")

encoder = body(encoder_path, "proof_kernel_encode_annotated_depth_with_work")
assert "Ast::Expr.DictLit(_, _)" in encoder
assert 'proof_kernel_add_node(nodes, "quantifier", quantifier_kind, range_index, body_index, statements.count' in encoder
print("quantifier arena admission: binder count matches dict range shape and metered range inspection")
