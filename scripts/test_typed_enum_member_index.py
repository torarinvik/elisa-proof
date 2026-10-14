"""Keep typed enum-member resolution on its owner-aware hash index."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
declarations = (ROOT / "src/proof/kernel_replay/type_declaration_index.elisa").read_text(encoding="utf-8")
variants = (ROOT / "src/proof/kernel_replay/enum_variant_typing.elisa").read_text(encoding="utf-8")
fixtures = (ROOT / "examples/kernel_proposition_identity_tests.elisa").read_text(encoding="utf-8")

typed_hash = declarations.split("def proof_kernel_replay_typed_enum_member_hash(", 1)[1].split(
    "def proof_kernel_replay_build_declaration_binding_index(", 1
)[0]
typed_lookup = declarations.split("def proof_kernel_replay_find_typed_enum_member_binding(", 1)[1].split(
    "def proof_kernel_replay_typing_binding_equal(", 1
)[0]
builder = declarations.split("def proof_kernel_replay_build_declaration_binding_index(", 1)[1].split(
    "def proof_kernel_replay_find_typed_enum_member_binding(", 1
)[0]
typed_call = variants.split("def proof_kernel_replay_enum_member_sort_for_type(", 1)[1].split(
    "def proof_kernel_replay_enum_type_path(", 1
)[0]
scoped_builder = (ROOT / "src/proof/kernel_replay/function_group_index.elisa").read_text(encoding="utf-8").split(
    "def proof_kernel_replay_build_scoped_typing_index(", 1
)[1].split("def proof_kernel_replay_function_group_charge_text(", 1)[0]
bare_lookup = variants.split("def proof_kernel_replay_enum_member_sort(", 1)[1].split(
    "def proof_kernel_replay_enum_member_sort_for_type(", 1
)[0]
scoped_lookup = variants.split("def proof_kernel_replay_enum_type_path(", 1)[1].split(
    "def proof_kernel_replay_enum_member_sort(", 1
)[0]

assert 'proof_kernel_replay_name_hash("enum-member-typed")' in typed_hash
assert "proof_kernel_replay_name_hash(name)" in typed_hash
assert "proof_kernel_replay_name_hash(owner)" in typed_hash
assert "owner_type_identity" in typed_hash
assert "enum_member_binding_heads[slot]" in typed_lookup
assert "enum_member_binding_next[row]" in typed_lookup
assert 'proof_kernel_replay_type_work_consume_amount(sview_len("enum-member-typed"), work)' in typed_lookup
assert "proof_kernel_replay_type_work_consume_amount(sview_len(name), work)" in typed_lookup
assert "proof_kernel_replay_type_work_consume_amount(sview_len(owner), work)" in typed_lookup
assert "not proof_kernel_replay_type_work_consume(work)" in typed_lookup
assert "binding.owner_type_identity == owner_identity" in typed_lookup
assert "binding.type_identity == owner_identity" in typed_lookup
assert 'name == "" or owner == "" or owner_identity == 0' in typed_lookup
assert "indexed_count: usize = total - index.value_overlay_count" in typed_lookup
assert "index.enum_member_binding_next.count != indexed_count" in typed_lookup
assert "row != indexed_count" in typed_lookup
assert "next: mutable ProofKernelReplayTypingIndex = inherited_index" in scoped_builder
assert "next.value_overlay_count <- local_count - next.value_overlay_start" in scoped_builder
assert "build_declaration_binding_index" not in scoped_builder
assert "indexed_binding_count: usize = typing_index.declaration_binding_next.count" in scoped_lookup
assert "typing_index.value_overlay_count > total_bindings" in scoped_lookup
assert "typing_index.declaration_binding_next.count != total_bindings - typing_index.value_overlay_count" in scoped_lookup
assert "row > indexed_binding_count" in scoped_lookup
assert "while row != indexed_binding_count and probes < indexed_binding_count" in scoped_lookup
assert "row >= typing_index.declaration_binding_next.count" in scoped_lookup
assert "row > indexed_binding_count" in scoped_lookup
assert "probes <- probes + 1" in scoped_lookup
assert "row != indexed_binding_count" in scoped_lookup
assert 'if binding.kind == "enum-member":' in builder
assert "proof_kernel_replay_typed_enum_member_hash(binding.name, binding.owner, binding.owner_type_identity)" in builder
assert "enum_member_next[row] <- enum_member_heads[member_slot]" in builder
assert "enum_member_heads[member_slot] <- row" in builder
assert 'sview_len("enum-member-typed")' in builder
assert "sview_len(binding.name)" in builder
assert "sview_len(binding.owner)" in builder
assert "proof_kernel_replay_find_typed_enum_member_binding" in typed_call
assert 'proof_kernel_replay_find_typing_binding(environment, typing_index, "enum-member"' in bare_lookup
assert '"enum-member", "Some", "Other"' in fixtures
assert "valid_other_qualified_member" in fixtures
assert '"binary", "==", other_value_root, other_some_member' in fixtures
assert "scoped_other_quantifier" in fixtures
assert '"quantifier", "forall", scoped_other_set, scoped_other_equality' in fixtures

print("typed enum-member resolution uses the bounded owner-aware index")
