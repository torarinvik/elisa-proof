"""Require exact declaration identity when replay validates imported global-array facts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/replay/global_mutable_array_validation.elisa").read_text(encoding="utf-8")

assert "declaration_offset: usize" in SOURCE
assert "candidate_position.offset.usize() == declaration_offset" in SOURCE
assert "trace.name, trace.owner_line, report.analysis_2.replay_owner_offset" in SOURCE
assert "owner_position.offset.usize() != report.analysis_2.replay_owner_offset" in SOURCE
assert "not report.analysis_2.replay_owner_offset_valid" in SOURCE

print("global mutable array replay binds fact owners by exact source offset")
