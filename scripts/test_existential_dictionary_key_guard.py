"""Existential dictionary replay must match overwrite semantics and fail closed."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
sources = (
    ROOT / "src/proof/kernel_replay/arena_child_validation.elisa",
    ROOT / "src/proof/kernel_replay/quantifiers_and_arena.elisa",
)


def body(name: str) -> str:
    for source in sources:
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


key_literal = body("proof_kernel_replay_existential_dictionary_key_literal_with_work")
assert 'nodes[root].kind == "typed-int"' in key_literal
assert 'nodes[root].operator != ""' in key_literal
assert 'nodes[root].kind != "int" or nodes[root].name != "" or nodes[root].value < 0' in key_literal
assert "ElisaProofKernelCore::typed_literal_value(nodes[root])" in key_literal
assert "nodes[root].name, literal.unsigned, literal.width" in key_literal
assert "proof_kernel_replay_arena_scalar_shape(nodes[root])" in key_literal
assert "not shape.known or not shape.valid" in key_literal
assert "proof_kernel_replay_constant_int_remaining_with_work_limit" not in key_literal
for field in ("kind", "operator", "name", "secondary_name"):
    assert f"sview_len(nodes[root].{field})" in key_literal
    assert "proof_kernel_replay_arena_shape_text_work_charge" in key_literal

unique = body("proof_kernel_replay_existential_dictionary_keys_unique_with_work")
assert "PROOF_KERNEL_REPLAY_MAX_QUANTIFIER_ENTRIES" in unique
assert "return false if work_used > work_limit" in unique
assert "capacity > work_limit / 2" in unique
assert "proof_kernel_replay_arena_shape_text_work_charge(capacity * 2, &work_used, reserve_before, work_limit)" in unique
assert "while probes < capacity and probes <= PROOF_KERNEL_REPLAY_INDEX_MAX_CLUSTER" in unique
assert "proof_kernel_replay_arena_shape_text_work_charge(1, &work_used, probe_before, work_limit)" in unique
assert "return false if current > key_index" in unique
assert "proof_kernel_replay_existential_dictionary_key_literal_with_work" in unique
assert "first_typed != key.typed" in unique
assert "prior_key.known" in unique
assert "key.bits == prior_key.bits and key.typed == prior_key.typed and key.sort == prior_key.sort and key.unsigned == prior_key.unsigned and key.width == prior_key.width" in unique
assert "sview_len(key.sort)" in unique
assert "sview_len(prior_key.sort)" in unique

arena = body("proof_kernel_replay_arena_children_valid_with_work")
assert 'if node.operator == "exists" and node.auxiliary == 2:' in arena
assert "proof_kernel_replay_existential_dictionary_keys_unique_with_work" in arena
direct = body("proof_kernel_replay_quantifier_remaining_with_work")
assert 'if kind == "exists" and quantifier.auxiliary == 2:' in direct
assert "proof_kernel_replay_existential_dictionary_keys_unique_with_work" in direct

direct = body("proof_kernel_replay_quantifier_remaining_with_work")
assert 'if kind == "exists" and quantifier.auxiliary == 2:' in direct
assert "proof_kernel_replay_existential_dictionary_keys_unique_with_work" in direct

forgery = (ROOT / "scripts/tests/portable_replay_kernel_forgeries.py").read_text(encoding="utf-8")
assert '"name": "wrapping-key-existential"' in forgery
assert 'append_node(dict_exists, "binary", "+", wrapped_key_left, wrapped_key_right)' in forgery
assert 'refused(dict_exists, "wrapping-key-existential", "rejected", "kernel-rejected")' in forgery
assert '"name": "single-key-existential-control"' in forgery
assert 'single_result["status"] == "replayed"' in forgery
assert '"name": "typed-duplicate-key-existential"' in forgery
assert 'refused(typed_dict_exists, "typed-duplicate-key-existential", "rejected", "kernel-rejected")' in forgery
assert 'typed_unique_result["status"] == "replayed"' in forgery
print("existential dictionary replay: duplicate/uncertain keys fail closed under metered literal checks")
