#!/usr/bin/env python3
"""Keep quantifier binder arity tied to the encoded range kind during arena admission."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
replay_path = ROOT / "src/proof/kernel_replay/quantifiers_and_arena.elisa"
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


arena_children = body(replay_path, "proof_kernel_replay_arena_children_valid_with_work")
assert 'node.kind == "quantifier"' in arena_children
quantifier_shape = body(replay_path, "proof_kernel_replay_quantifier_range_arity_valid")
assert "range: ElisaProofKernelCore::ProofKernelNode = nodes[node.left]" in quantifier_shape
assert "(node.auxiliary == 1 and range.kind != \"dict\") or (node.auxiliary == 2 and range.kind == \"dict\")" in quantifier_shape
assert "proof_kernel_replay_arena_shape_text_work_charge(sview_len(range.kind), &work_used, range_kind_work_before, work_limit)" in arena_children
assert "proof_kernel_replay_quantifier_range_arity_valid(nodes, node)" in arena_children

encoder = body(encoder_path, "proof_kernel_encode_annotated_depth_with_work")
assert "Ast::Expr.DictLit(_, _)" in encoder
assert 'proof_kernel_add_node(nodes, "quantifier", quantifier_kind, range_index, body_index, statements.count' in encoder
print("quantifier arena admission: binder count matches dict range shape and metered range inspection")
