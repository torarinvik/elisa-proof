"""Bind pop-snapshot parameter typing to the exact replayed function declaration."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
lookup_source = (ROOT / "src/proof/check/operator_witnesses.elisa").read_text(encoding="utf-8")
replay_source = (ROOT / "src/proof/replay/source_binding_validation/pop_scalar_snapshots.elisa").read_text(encoding="utf-8")

lookup = lookup_source.split(
    "def proof_scalar_reference_parameter_type_at_owner_offset_with_work(", 1
)[1].split("const PROOF_PURE_CALL_WITNESS_DEPTH_LIMIT", 1)[0]
assert "owner_offset_valid" in lookup
assert "position.line != owner_line" in lookup
assert "position.offset.usize() != owner_offset" in lookup
assert "count <- count + 1" in lookup
assert "Ast::Decl.Module(_, body, _) | Ast::Decl.Scoped(body, _)" in lookup
assert "proof_scalar_reference_parameter_type_at_owner_offset_with_work(body" in lookup

assert "proof_replay_local_binding_parameter_name_present_at_offset_with_work" in replay_source
assert "proof_scalar_reference_parameter_type_at_owner_offset_with_work" in replay_source
assert "proof_resource_type_marker_summary_for_owner_at_offset_with_work" in replay_source
assert "proof_scalar_reference_parameter_type_in_declarations_with_work(report.source.source_declarations, trace.name, receiver" not in replay_source

print("pop-snapshot replay resolves parameter type and shadowing at the exact owner offset")
