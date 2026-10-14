"""Require exact declaration identity for call summaries in source requires clauses."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/replay/summary_call_source_sites.elisa").read_text(encoding="utf-8")
GENERIC_CALLERS = (
    ("src/proof/replay/global_mutable_array_validation.elisa", "owner_line, report.analysis_2.replay_owner_offset"),
    ("src/proof/replay/summary_call_sites.elisa", "owner_line, owner_offset"),
    ("src/proof/replay/certificate_validation_integrated_helpers.elisa", "owner_line, report.analysis_2.replay_owner_offset"),
)

assert "owner_offset: usize" in SOURCE
assert "position.offset.usize() == owner_offset" in SOURCE
assert "owner_offset: usize = report.analysis_2.replay_owner_offset" in SOURCE
assert "not report.analysis_2.replay_owner_offset_valid" in SOURCE
assert "trace.name, owner_line, owner_offset, call" in SOURCE
assert "owner_line == 0" in SOURCE
assert "position.line == owner_line and position.offset.usize() == owner_offset" in SOURCE
signature_check = SOURCE.split("def proof_replay_summary_signature_requires_call_source_site(", 1)[1].split("\n        def ", 1)[0]
assert "proof_replay_trace_owner_source_position_for_trace_with_work(report, trace, work)" in signature_check
assert "owner_position.offset.usize() != owner_offset" in signature_check
assert "proof_replay_trace_owner_source_position_line_for_trace_with_work" not in signature_check
for relative_path, expected in GENERIC_CALLERS:
    caller = (ROOT / relative_path).read_text(encoding="utf-8")
    assert expected in caller, relative_path

print("source-call replay binds declaration scans to the exact certificate owner")
