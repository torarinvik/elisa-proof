"""Drop-risk generic classification must use the declaring type's exact source owner."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/check/drop_type_index.elisa").read_text(encoding="utf-8")
lookup = source.split("def proof_source_drop_generic_index_lookup(", 1)[1].split(
    "def proof_source_drop_index_collect(", 1
)[0]
assert "owner_offset: u32" in lookup and "owner_offset_valid: bool" in lookup
assert "proof_source_generic_owner_param_present_in_index_with_work(name, declaration_line, owner_offset" in lookup

classifier = source.split("def proof_source_drop_index_type_may_drop(", 1)[1].split(
    "def proof_source_drop_index_expand_aliases(", 1
)[0]
assert "proof_source_drop_generic_index_lookup(name, declaration_line, owner_offset, owner_offset_valid" in classifier
assert "generic_index, declaration_line, owner_offset, owner_offset_valid, source_work, depth + 1" in classifier

declarations = source.split("def proof_source_drop_index_expand_declarations(", 1)[1].split(
    "def proof_source_drop_type_index_with_work(", 1
)[0]
assert "generic_index, position.line, position.offset, true, source_work, 0" in declarations

print("drop-risk generic classification uses exact struct and enum owner offsets")
