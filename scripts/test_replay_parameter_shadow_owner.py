"""Ensure replay parameter-shadow checks cannot stop at a same-line sibling."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/replay/source_binding_validation.elisa").read_text(encoding="utf-8")
helper = source.split(
    "def proof_replay_local_binding_parameter_name_present_with_work(", 1
)[1].split("def proof_replay_local_binding_parameter_name_present_at_offset_with_work(", 1)[0]
matched_candidate = helper.split("if name == owner and position.line == owner_line:", 1)[1].split(
    "Ast::Decl.Module", 1
)[0]
assert "found: mutable bool = false" in helper
assert "found <- true if parameter.name == parameter_name" in matched_candidate
assert "return false" not in matched_candidate
assert "found <- true if proof_replay_local_binding_parameter_name_present_with_work(nested" in helper

exact = source.split(
    "def proof_replay_local_binding_parameter_name_present_at_offset_with_work(", 1
)[1].split("def proof_replay_local_binding_parameter_name_present_for_report_owner_with_work(", 1)[0]
assert "position.line == owner_line and position.offset.usize() == owner_offset" in exact
report_owner = source.split(
    "def proof_replay_local_binding_parameter_name_present_for_report_owner_with_work(", 1
)[1].split("# A truncated or unrecognized declaration walk", 1)[0]
assert "report.analysis_2.replay_owner_offset_valid" in report_owner
assert "owner_line == report.analysis_2.replay_owner_line" in report_owner

for relative in (
    "src/proof/replay/entry_count_source.elisa",
    "src/proof/replay/summary_call_sites.elisa",
    "src/proof/replay/certificate_owner_paths.elisa",
    "src/proof/replay/source_binding_validation/mutable_local_bindings.elisa",
    "src/proof/replay/source_binding_validation/loop_entry_certificates.elisa",
):
    assert "proof_replay_local_binding_parameter_name_present_for_report_owner_with_work" in (
        ROOT / relative
    ).read_text(encoding="utf-8")

print("replay parameter-shadow checks scan sibling owners and use offsets when available")
