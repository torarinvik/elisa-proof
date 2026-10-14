"""Keep threaded-summary generic checks bound to exact source declaration identity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / "src/proof/replay/source_generic_parameter_index.elisa").read_text(encoding="utf-8")
generic_walk = (ROOT / "src/proof/replay/threaded_type_generics.elisa").read_text(encoding="utf-8")
threaded = (ROOT / "src/proof/replay/threaded_summaries.elisa").read_text(encoding="utf-8")

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
assert "report.analysis_2.replay_owner_offset, report.analysis_2.replay_owner_offset_valid" in threaded
assert "proof_resource_type_marker_summary_for_owner_at_offset_with_work" in threaded

print("threaded summary generic checks use exact owner offsets and shared work")
