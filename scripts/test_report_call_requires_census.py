"""Pin API-bound source coverage for ordinary call-requires rows."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CENSUS = (ROOT / "src/proof/model/report_call_requires_census.elisa").read_text(encoding="utf-8")
RESOLUTION = (ROOT / "src/proof/model/report_call_requires_resolution.elisa").read_text(encoding="utf-8")
API = (ROOT / "src/proof/replay/api.elisa").read_text(encoding="utf-8")
MAIN = (ROOT / "src/main.elisa").read_text(encoding="utf-8")


def body(source: str, name: str) -> str:
    markers = (f"def {name}(", f"def {name}[")
    starts = [source.find(marker) for marker in markers]
    starts = [start for start in starts if start >= 0]
    assert len(starts) == 1, (name, starts)
    start = starts[0]
    marker = next(marker for marker in markers if source.find(marker) == start)
    following = source.find("\n        def ", start + len(marker))
    return source[start:] if following < 0 else source[start:following]


census = body(CENSUS, "proof_report_call_requires_census")
expected_rows = body(CENSUS, "proof_report_call_requires_expected_rows")
expected_index = body(CENSUS, "proof_report_call_requires_expected_index_build")
selected_match = body(RESOLUTION, "proof_report_call_requires_selected_source_match")
assert "source.file.top_decls" in census
assert "source.file_identity != report.source.source_file_identity" in census
assert "focus_function != report.context.focused_function" in census
assert "focus_function == \"\"" in census  # Full report schedules every local executable row.
assert "scheduled[target] <- true" in census  # Focus mode starts from the API selector.
assert "pending.push(row) if rows[row].executable" in census  # Full mode validates all executable call edges.
assert "scheduled_owners.push(ProofSourceScheduledOwner{name: rows[row].name, line: rows[row].line, offset: rows[row].offset})" in census
assert "proof_report_call_requires_census_dependency_edges(source.file, rows[caller].line" in census
assert "report.context.focused_function_identity_valid" not in census
assert "report.context.focused_function_offset" not in census
assert "Ast::Decl.Import" in census and "Ast::Decl.Extern" in census
assert "Ast::Decl.Module" in census and "Ast::Decl.Scoped" in census
assert "Ast::Decl.Const(_, type_expression, initializer" in census
assert "proof_expr_has_call_with_work(type_expression" in census
assert "proof_expr_has_call_with_work(initializer" in census
assert "Ast::Expr.Call(Ast::Expr.Ident(callee_name" in census
assert "argument_names.count != 0" in census

# Expected source keys are derived before event matching, so deleting any producer
# row for a source site must fail. Repeated visits are counted exactly per source key.
assert "for requires_index in 0..<rows[target].signature_requires.count" in expected_rows
assert "parameter.has_default" in expected_rows
assert "visit_count: 1" in expected_rows
assert "contract_index: contract_index" in expected_rows
assert "row.contract_index.i64()" not in body(CENSUS, "proof_report_call_requires_expected_hash")
assert "left.contract_index == right.contract_index" not in body(CENSUS, "proof_report_call_requires_expected_key_equal")
assert "prior.contract_index != item.contract_index" in expected_index
assert "source.file.signature_contract_lines[contract_index] != rows[owner].line" in census
assert 'kind not in {"requires", "ensures", "ensure"}' in census
assert "same_line_declarations != 1" in census
assert "for declaration in source.file.top_decls |declaration, rows, owner" in census
assert "Ast::Decl.Func(_, _, _, _, _, _, position) | Ast::Decl.Extern(_, _, _, _, _, _, _, position)" in census
assert "proof_report_call_requires_collect_runtime_expression(source.file.signature_contract_exprs[contract_index]" in census
assert census.count("proof_report_call_requires_expected_index_find(expected_index, expected, key, source_work)") == 2
assert "expected[current].visit_count <- expected[current].visit_count + item.visit_count" in expected_index
assert "expected[row].visit_count <- 0" in expected_index
assert "event_counts.push(0)" in census and "attempt_counts.push(0)" in census
assert "event_counts[matched.row] >= expected[matched.row].visit_count" in census
assert "attempt_counts[matched.row] >= expected[matched.row].visit_count" in census
assert "event_counts[row] != expected[row].visit_count or attempt_counts[row] != expected[row].visit_count" in census
# Keep all emitted rows source matched while permitting repeat visits at a valid key.
assert "for event in report.results.obligation_inventory" in census
assert "for attempt in report.results.goal_attempts" in census
assert "return false if not matched.complete or not matched.found" in census
assert "call_contract_rows" in selected_match
assert "proof_report_call_requires_collect_runtime_expression(expression," in selected_match
assert "selected_contract_row <- call_contract_rows[row]" in selected_match
assert "selected_contract_row < report.source_contracts.source_signature_contract_lines.count" in selected_match
assert "report.source_contracts.source_signature_contract_lines[selected_contract_row] != attempt.owner_function_line" in selected_match

# The final receipt path passes the original API selector and parser-derived schedule
# into structural coverage and typed replay before issuing any source authority.
assert 'source_structure_failure: mutable sview' in API
assert "proof_source_analysis_report_structure_bound_failure(view_source, report, scheduled_owners, source_binding_complete, &source_work)" in API
assert "proof_report_call_requires_census(view_source, report, focus_function, &scheduled_owners, &source_work)" in API
assert '"source-call-requires-coverage"' in API
assert 'include "./proof/model/report_call_requires_census.elisa"' in MAIN

print("call-requires source census: whole-site deletion and missing selected attempts fail closed")
