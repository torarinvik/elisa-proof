"""Keep threaded-summary generic checks bound to exact source declaration identity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / "src/proof/replay/source_generic_parameter_index.elisa").read_text(encoding="utf-8")
generic_walk = (ROOT / "src/proof/replay/threaded_type_generics.elisa").read_text(encoding="utf-8")
threaded = (ROOT / "src/proof/replay/threaded_summaries.elisa").read_text(encoding="utf-8")
structural_cache = (ROOT / "src/proof/replay/structural_source_cache_validation.elisa").read_text(encoding="utf-8")
type_markers = (ROOT / "src/proof/replay/threaded_type_markers.elisa").read_text(encoding="utf-8")

exact_lookup = index.split(
    "def proof_replay_source_generic_param_owner_name_count_with_work(", 1
)[1].split("def proof_replay_call_generic_function_owner(", 1)[0]
assert "proof_source_generic_owner_param_present_with_work" in exact_lookup
assert "owner_offset > 4294967295" in exact_lookup
assert "not owner_offset_valid" in exact_lookup

assert "proof_replay_source_generic_param_owner_name_count_with_work" in generic_walk
assert "declaration_line >= 2147483648" not in generic_walk
assert "owner_offset_valid" in generic_walk
assert "|argument, declaration_line, owner_offset, owner_offset_valid, report, source_work, depth|" in generic_walk
assert "|element, declaration_line, owner_offset, owner_offset_valid, report, source_work, depth|" in generic_walk
assert "position.offset.usize(), true" in threaded
assert "source_report.analysis_2.replay_owner_offset, source_report.analysis_2.replay_owner_offset_valid" in threaded
assert "proof_resource_type_marker_summary_for_owner_at_offset_with_work" in threaded

# Builtin marker spellings must not bypass a visible source alias or nominal declaration.
direct_markers = type_markers.split(
    "def proof_replay_thread_direct_type_markers(", 1
)[1].split("def ", 1)[0]
assert direct_markers.index("if builtin:") < direct_markers.index("proof_replay_thread_nearest_type_declaration")
assert "not nearest.complete or nearest.count > 0" in direct_markers
assert "proof_replay_thread_import_shadow_check(report, name, owner_path, work)" in direct_markers
assert direct_markers.index("if declaration.count == 0:") < direct_markers.index("proof_replay_thread_nearest_type_declaration")

# The function generic-row census must ignore compiler generic-identity markers for
# non-function declarations while still requiring every function marker to have a row.
generic_auth = structural_cache.split(
    "def proof_replay_structural_generic_rows_authenticate(", 1
)[1].split("def proof_replay_structural_validation_cache_build(", 1)[0]
assert 'annotation.name != "__generic_param_identity" or annotation.line != 3900000131' in generic_auth
assert "proof_source_conversion_generic_function_owner_lookup(annotation.detail_line, annotation.offset.usize(), report)" in generic_auth
assert "function_rows != function_markers" in generic_auth
assert "generic_owner_index_entries != function_rows" not in generic_auth

print("threaded summary generic checks use exact owner offsets and shared work")
