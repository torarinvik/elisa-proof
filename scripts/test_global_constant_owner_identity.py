"""Require exact certificate-owner identity for replayed global-constant facts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/replay/global_constant_validation.elisa").read_text(encoding="utf-8")

assert "owner_offset: usize" in SOURCE
assert "candidate_position.offset.usize() == owner_offset" in SOURCE
assert "trace.name, trace.owner_line, report.analysis_2.replay_owner_offset" in SOURCE
assert "trace.owner_line != 0 and not report.analysis_2.replay_owner_offset_valid" in SOURCE
assert "candidate_position.offset.usize() == owner_offset" in SOURCE
assert "owner_line, owner_offset, &next_scope.scope" in SOURCE

print("global constant replay binds fact owners by exact source offset")
