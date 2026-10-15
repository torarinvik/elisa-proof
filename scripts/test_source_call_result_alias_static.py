"""Keep local-result alias replay closed over borrows and scoped-name shadowing."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/proof/replay/call_result_binding_provenance.elisa"
lines = SOURCE.read_text(encoding="utf-8").splitlines()
start = next(i for i, line in enumerate(lines) if re.match(r"\s*def proof_replay_call_result_binding_expr_borrows\b", line))
indent = len(lines[start]) - len(lines[start].lstrip())
body = [lines[start]]
for line in lines[start + 1 :]:
    if line.strip() and len(line) - len(line.lstrip()) <= indent:
        break
    body.append(line)
borrow_scan = "\n".join(body)
assert "operator == TokenKind.Ampersand or operator == TokenKind.Mutable or operator == TokenKind.Lmut" in borrow_scan
assert "proof_replay_call_result_binding_mentions_with_work(inner, name, source_work)" in borrow_scan
assert "Ast::Expr.Invalid:\n                    return true" in borrow_scan
source = SOURCE.read_text(encoding="utf-8")
scoped_signature = source.split("def proof_replay_call_result_binding_scoped_signature(", 1)[1].split("\n        def ", 1)[0]
assert "report.analysis_2.replay_owner_offset_valid" in scoped_signature
assert "proof_replay_deterministic_qualified_declaration" in scoped_signature
assert "matches != 1" in scoped_signature
assert "Ast::Expr.Scope(_, _, _):\n                                            return false if not proof_replay_call_result_binding_scoped_signature" in source
scoped_target_source = (ROOT / "src/proof/replay/source_call_scoped_target.elisa").read_text(encoding="utf-8")
scoped_target = scoped_target_source.split("def proof_replay_call_scoped_target_site(", 1)[1].split("\n        def ", 1)[0]
scope_root = scoped_target_source.split("def proof_replay_call_scope_base_has_bound_root(", 1)[1].split("\n        def ", 1)[0]
assert "proof_replay_call_scope_base_has_bound_root(base, bindings, work, 0)" in scoped_target
assert "return true if depth >= 96 or not proof_replay_call_work_add(work, 1)" in scope_root
assert "bound == root_name" in scope_root
assert "Ast::Expr.Scope(inner_base, _, _)" in scope_root
assert "Ast::Expr.Paren" not in scope_root
owner_scan = source.split("def proof_replay_call_result_binding_owner(", 1)[1].split("\n        def ", 1)[0]
assert "proof_replay_owner_work_charge(1, source_work)" in owner_scan
assert "proof_replay_owner_work_charge(sview_len(candidate), source_work)" in owner_scan
assert "proof_replay_owner_work_charge(sview_len(owner), source_work)" in owner_scan
print("source call-result alias: borrows and scoped-name shadowing remain fail-closed")
