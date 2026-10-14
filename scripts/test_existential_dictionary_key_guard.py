"""Existential dictionary replay must match overwrite semantics and fail closed."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "src/proof/kernel_replay/quantifiers_and_arena.elisa"


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


key_literal = body("proof_kernel_replay_existential_dictionary_key_literal_with_work")
assert 'nodes[root].kind != "int"' in key_literal
assert 'nodes[root].operator != ""' in key_literal
assert 'nodes[root].name != "" or nodes[root].value < 0' in key_literal
assert "proof_kernel_replay_constant_int_remaining_with_work_limit" not in key_literal
assert "proof_kernel_replay_int_tagged" not in key_literal
for field in ("kind", "operator", "name"):
    assert f"sview_len(nodes[root].{field})" in key_literal
    assert "proof_kernel_replay_arena_shape_text_work_charge" in key_literal

unique = body("proof_kernel_replay_existential_dictionary_keys_unique_with_work")
assert "PROOF_KERNEL_REPLAY_MAX_QUANTIFIER_ENTRIES" in unique
assert "pair_count > work_limit - work_used" in unique
assert "proof_kernel_replay_existential_dictionary_key_literal_with_work" in unique
assert "left_key.value == right_key.value" in unique

arena = body("proof_kernel_replay_arena_children_valid_with_work")
assert 'if node.operator == "exists" and node.auxiliary == 2:' in arena
assert "proof_kernel_replay_existential_dictionary_keys_unique_with_work" in arena

forgery = (ROOT / "scripts/tests/portable_replay_kernel_forgeries.py").read_text(encoding="utf-8")
assert '"name": "duplicate-key-existential"' in forgery
assert '"name": "single-key-existential-control"' in forgery
assert 'refused(dict_exists, "duplicate-key-existential", "rejected", "kernel-rejected")' in forgery
assert 'single_result["status"] == "replayed"' in forgery
print("existential dictionary replay: duplicate/uncertain keys fail closed under metered literal checks")
