"""Certificate-scoped owner body lookup must use exact source declaration identity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/replay/source_local_writes.elisa").read_text(encoding="utf-8")
BINDING_SOURCE = (ROOT / "src/proof/replay/source_binding_validation.elisa").read_text(encoding="utf-8")

assert "proof_replay_local_binding_find_owner_at_offset_with_work" in SOURCE
assert "position.line == owner_line and position.offset.usize() == owner_offset" in SOURCE
assert "if report.analysis_2.replay_owner_offset_valid:" in SOURCE
assert "report.analysis_2.replay_owner_offset, body" in SOURCE
assert "return matches == 1" in SOURCE
assert "report.analysis_2.replay_owner_line != owner_line" in SOURCE
assert "proof_replay_local_binding_find_owner_with_work(report.source.source_declarations" in SOURCE
assert 'proof_replay_result_symbol_preservation_loop_site_with_work(report, body, body, consumer, dummy_position, ""' in BINDING_SOURCE
alias_scan = SOURCE.split("def proof_replay_source_local_lambda_writes_body", 1)[1].split(
    "def proof_replay_source_expr_calls_mutating_local_lambda", 1
)[0]
assert "Ast::Stmt.VarDecl(local_name, _, _, declaration_position)" in alias_scan
assert "return true if local_name == callable and declaration_position.offset > 0 and declaration_position.offset < call_position.offset" in alias_scan
assert "proof_replay_mutable_local_body_work_charge(lambda_body, work, 0)" in alias_scan
assert "proof_replay_source_body_touches([], lambda_body, tracked, true, 0)" in alias_scan
assert "proof_replay_source_body_has_call(lambda_body, work, 0)" in alias_scan
assert "proof_replay_source_touch_work_charge(1, work)" in alias_scan
assert "proof_replay_source_local_lambda_writes_body(body, callable, tracked, position, work, 0)" in SOURCE
assert "proof_replay_source_expr_calls_mutating_local_lambda(owner_body, expression, name, source_work, 0)" in (
    ROOT / "src/proof/replay/summary_local_alias_sites.elisa"
).read_text(encoding="utf-8")
assert "proof_replay_source_expr_calls_mutating_local_lambda(owner_body, expression, tracked_local, source_work, 0)" in (
    ROOT / "src/proof/replay/source_binding_validation/result_symbols.elisa"
).read_text(encoding="utf-8")

print("certificate-scoped source owner body lookup uses exact offsets")
