"""Certificate-scoped owner body lookup must use exact source declaration identity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/replay/source_local_writes.elisa").read_text(encoding="utf-8")

assert "proof_replay_local_binding_find_owner_at_offset_with_work" in SOURCE
assert "position.line == owner_line and position.offset.usize() == owner_offset" in SOURCE
assert "if report.analysis_2.replay_owner_offset_valid:" in SOURCE
assert "report.analysis_2.replay_owner_offset, body" in SOURCE
assert "return matches == 1" in SOURCE
assert "report.analysis_2.replay_owner_line != owner_line" in SOURCE
assert "proof_replay_local_binding_find_owner_with_work(report.source.source_declarations" in SOURCE

print("certificate-scoped source owner body lookup uses exact offsets")
