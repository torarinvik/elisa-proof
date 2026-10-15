"""Pin exact loop-invariant source admission and recursive coverage."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = [line]
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"function {name} not found in {path}")

path = ROOT / "src/proof/model/report_loop_invariant_admission.elisa"
attempt_admission = function_body(ROOT / "src/proof/model/report_goal_admission.elisa", "proof_report_goal_source_admissible_after_structure_internal")
attempt = function_body(path, "proof_source_loop_invariant_goal_attempt_admitted_with_declarations")
attempt_wrapper = function_body(path, "proof_source_loop_invariant_goal_attempt_admitted")
source_scan = function_body(path, "proof_source_loop_invariant_goal_matches_declarations")
statement_scan = function_body(path, "proof_source_loop_invariant_scan_body")
coverage = function_body(path, "proof_source_loop_invariant_entry_coverage_declarations")
coverage_walk = function_body(path, "proof_source_loop_invariant_coverage_body")
coverage_loop = function_body(path, "proof_source_loop_invariant_coverage_loop")
coverage_clause = function_body(path, "proof_source_loop_invariant_coverage_clause")
source_coverage = function_body(path, "proof_source_loop_invariant_source_coverage_with_declarations")
coverage_expression = function_body(path, "proof_source_loop_invariant_coverage_expression")
scan_expression = function_body(path, "proof_source_loop_invariant_scan_expression")
preservation_gate = function_body(path, "proof_source_loop_invariant_preservation_required")
statement_flow = function_body(path, "proof_source_loop_statement_flow")
body_flow = function_body(path, "proof_source_loop_body_may_fallthrough")
match_catchall = function_body(path, "proof_source_loop_match_catchall")
match_is_catch = function_body(path, "proof_source_loop_match_is_catch")
match_exits = function_body(path, "proof_source_loop_match_fully_exits")
for gate in (
    'attempt.source_phase != "loop-invariant-entry"',
    'attempt.source_phase != "loop-invariant-preservation"',
    "loop_matches != 1 or invariant_matches != 1",
    "not certificate.replayed",
    "certificate.source_phase != attempt.source_phase",
):
    assert gate in attempt, gate
assert "proof_source_loop_invariant_goal_attempt_admitted_with_declarations(report.source.source_declarations, report, goal_id, source_work, false)" in attempt_wrapper
assert "source_coverage_checked: bool = false" in attempt
assert "if not source_coverage_checked:" in attempt
assert "function_position.offset != attempt.owner_function_offset" in source_scan
assert "function_position.line != attempt.owner_function_line" in source_scan
for recursive_case in (
    "Ast::Stmt.Block(kind, _, _, nested, _)",
    "Ast::Stmt.If(condition, then_body, else_body, _)",
    "Ast::Stmt.Match(scrutinee, arms, _)",
):
    assert recursive_case in statement_scan, recursive_case
assert 'kind != "assert_by" and not proof_source_loop_invariant_scan_body(nested' in statement_scan
assert "Ast::Stmt.If(condition, then_body, else_body, _)" in coverage_walk
assert "Ast::Stmt.Match(scrutinee, arms, _)" in coverage_walk
assert "proof_source_loop_invariant_coverage_expression(scrutinee" in coverage_walk
assert "proof_source_loop_invariant_coverage_expression(arm.guard" in coverage_walk
assert "Ast::Stmt.Contract(_, expression, _)" in coverage_walk
assert "Ast::Stmt.Invalid:" in coverage_walk and "return false" in coverage_walk
assert 'kind != "assert_by" and not proof_source_loop_invariant_coverage_body(nested' in coverage_walk
assert "Ast::Stmt.While(condition, nested, position)" in coverage_walk
assert "Ast::Stmt.For(_, _, iterable, nested, position)" in coverage_walk
assert "proof_source_loop_invariant_coverage_loop(condition, nested, position" in coverage_walk
assert "proof_source_loop_invariant_coverage_loop(iterable, nested, position" in coverage_walk
coverage_loop = function_body(path, "proof_source_loop_invariant_coverage_loop")
assert "proof_source_loop_invariant_coverage_expression(header" in coverage_loop
assert "proof_source_loop_invariant_coverage_body(nested" in coverage_loop
assert "Ast::Expr.BoolLit(true, position), 2" in coverage_loop, "same-line loop ambiguity must remain fail-closed"
scan_loop = function_body(path, "proof_source_loop_invariant_scan_loop")
assert "kind != \"invariant\"" in scan_loop
assert "proof_source_loop_invariant_scan_loop(condition, nested, position" in statement_scan
assert "proof_source_loop_invariant_scan_loop(iterable, nested, position" in statement_scan
assert "proof_source_loop_invariant_scan_expression(header" in scan_loop
assert "proof_source_loop_invariant_scan_body(nested" in scan_loop
assert "proof_source_loop_invariant_coverage_body(body" in coverage
assert "depth >= PROOF_SOURCE_LOOP_INVARIANT_DEPTH_LIMIT" in coverage_walk
assert "proof_source_loop_invariant_coverage_body(nested" in coverage_walk
assert "proof_source_loop_invariant_coverage_clause(name, function_position, position, expression, preservation_required" in coverage_loop
for statement_expression in (
    "Ast::Stmt.Return(expression, _) | Ast::Stmt.Expr(expression, _)",
    "Ast::Stmt.VarDecl(_, type_expression, initializer, _)",
    "Ast::Stmt.Assign(target, _, initializer, _)",
):
    assert statement_expression in coverage_walk, statement_expression
assert "Ast::Expr.Block(statements, value, _, _)" in coverage_expression
assert "proof_source_loop_invariant_coverage_body(statements" in coverage_expression
assert "Ast::Expr.Lambda(_, body, _)" in coverage_expression
assert "Ast::Expr.GetElse(base, recovery, _)" in coverage_expression
assert "candidate.effect_type" in coverage_expression
assert "candidate.effect_type" in scan_expression
assert "depth >= PROOF_SOURCE_LOOP_INVARIANT_DEPTH_LIMIT" in coverage_expression
assert "expected.push(proof_source_loop_invariant_coverage_key(name, function_position, loop_position, expression, 0))" in coverage_clause
assert "expected.push(proof_source_loop_invariant_coverage_key(name, function_position, loop_position, expression, 1))" in coverage_clause
assert "for attempt in report.results.goal_attempts" not in coverage_clause, "each source clause must not rescan the report attempts"
assert "proof_source_loop_transfer_index_create(expected.count, source_work)" in source_coverage
assert "proof_source_loop_transfer_index_insert(&index, &groups, expected_row, source_work)" in source_coverage
assert "if group.key.phase == 2:" in source_coverage and "group.expected_clause_count != 1" in source_coverage
assert "for goal_id in 0..<report.results.goal_attempts.count" in source_coverage
assert 'attempt.source_phase == "loop-invariant-entry" or attempt.source_phase == "loop-invariant-preservation"' in source_coverage
assert 'preservation: bool = attempt.source_phase == "loop-invariant-preservation"' in source_coverage
assert "proof_source_loop_invariant_coverage_key(attempt.name, Ast::Pos{line: attempt.owner_function_line, column: 0, offset: attempt.owner_function_offset, end_line: 0, end_column: 0, end_offset: 0}, attempt.loop_source_position, attempt.goal, 1 if preservation else 0)" in source_coverage
assert "proof_source_loop_transfer_index_find(index, groups, key, source_work)" in source_coverage
assert "not matched.complete or not matched.found or matched.group_id >= groups.count" in source_coverage
assert "groups[matched.group_id].matched_attempt_count >= groups[matched.group_id].expected_clause_count" in source_coverage
assert "group.matched_attempt_count != group.expected_clause_count" in source_coverage
assert "proof_source_loop_invariant_goal_attempt_admitted_with_declarations(declarations, report, goal_id" not in source_coverage
assert "proof_source_loop_body_may_fallthrough(body, annotations, source_work, 0)" in preservation_gate
assert "not flow.complete or flow.may_fallthrough" in preservation_gate
assert 'return catch_match and type_name == "error"' in match_catchall
assert 'annotation.owner == "__catch_match" and annotation.name == "__catch_match"' in match_is_catch
assert "annotation.line != position.line or annotation.offset != position.offset" in match_is_catch
assert "proof_source_loop_match_catchall(last_pattern, catch_state.is_catch, 0)" in match_exits
assert "Ast::Expr.Absent" in match_exits and "return (true, false)" in match_exits
assert "Ast::Stmt.Return(_, _) | Ast::Stmt.Break(_, _) | Ast::Stmt.Continue(_, _)" in statement_flow
assert "then_flow.may_fallthrough or else_flow.may_fallthrough" in statement_flow
assert 'return (true, true) if kind == "assert_by"' in statement_flow
assert "Ast::Stmt.While(_, _, _) | Ast::Stmt.For(_, _, _, _, _)" in statement_flow
assert "Ast::Stmt.Invalid:" in statement_flow and "(false, true)" in statement_flow
assert "return (false, true) if not flow.complete" in body_flow

producer = function_body(ROOT / "src/proof/check/function_contracts_and_frames.elisa", "proof_check_loop_control_invariants")
loop_certifier = function_body(ROOT / "src/proof/check/returns/loops.elisa", "proof_certify_loop_invariant_goal")
replay = function_body(ROOT / "src/proof/replay/fact_trace_validation.elisa", "proof_replay_attempt_matches_certificate_with_limit")
transfer_path = ROOT / "src/proof/model/report_loop_transfer_admission.elisa"
transfer_walk = function_body(transfer_path, "proof_source_loop_transfer_collect_loop_body")
transfer_admission = function_body(transfer_path, "proof_source_loop_transfer_attempt_admitted")
transfer_key = function_body(transfer_path, "proof_source_loop_transfer_key_equal")
transfer_index_insert = function_body(transfer_path, "proof_source_loop_transfer_index_insert")
transfer_index_find = function_body(transfer_path, "proof_source_loop_transfer_index_find")
transfer_coverage = function_body(transfer_path, "proof_source_loop_transfer_source_coverage")
report_admission = function_body(ROOT / "src/proof/model/report_invariants.elisa", "proof_report_source_admission_failure")
goal_admission_with_snapshots = function_body(ROOT / "src/proof/model/report_goal_admission.elisa", "proof_report_goal_source_admissible_after_structure_with_snapshots")
assert 'report.context.current_loop_invariant_phase <- "loop-invariant-transfer"' in producer
assert 'proof_certify_loop_invariant_goal(facts, goal, report, functions, transfer_position.line, name, annotations, "loop-invariant-transfer")' in producer
assert "goal_attempts[goal_id].loop_transfer_position <- transfer_position" in producer
assert "certificates[certificate_index].loop_transfer_position <- transfer_position" in producer
assert "proof_expression_has_fresh_runtime_value(goal, functions, 0)" in loop_certifier
assert "not proof_contract_calls_are_pure(goal, functions)" in loop_certifier
assert 'attempt.source_phase == "loop-invariant-transfer" and not proof_replay_source_position_equal(attempt.loop_transfer_position, certificate.loop_transfer_position)' in replay
assert 'elif attempt.source_phase == "loop-invariant-transfer":' in attempt_admission
assert "event_admitted <- proof_source_loop_transfer_attempt_admitted(report, goal_id, source_work)" in attempt_admission
assert 'attempt.source_phase != "loop-invariant-transfer"' in transfer_admission
assert 'attempt.rule != "goal"' in transfer_admission
assert "transfer.offset > 0" in transfer_admission
assert "transfer.end_offset > transfer.offset" in transfer_admission
assert "proof_source_loop_transfer_key_equal(key, groups[group_id].key, source_work)" in transfer_index_find
assert "loop_transfers_covered: bool = proof_source_loop_transfer_source_coverage(report, &source_work)" in report_admission
assert report_admission.count("proof_source_loop_invariant_source_coverage(report, &source_work)") == 2
assert "goal_finding_clear, true, true, source_work)" in goal_admission_with_snapshots, "snapshot admission skips per-attempt AST scans only after source structure coverage"
assert "ProofSourceLoopTransferExpectation{owner_name: attempt.name, owner_line: attempt.owner_function_line, owner_offset: attempt.owner_function_offset, position: attempt.loop_transfer_position, invariant: attempt.goal}" in transfer_coverage
assert "not match_result.complete or not match_result.found or match_result.group_id >= groups.count" in transfer_coverage
assert "expected_clause_count: 1" in transfer_index_insert
assert "groups[group_id].expected_clause_count <- groups[group_id].expected_clause_count + 1" in transfer_index_insert
assert "groups[match_result.group_id].matched_attempt_count >= groups[match_result.group_id].expected_clause_count" in transfer_coverage
assert "groups[match_result.group_id].matched_attempt_count <- groups[match_result.group_id].matched_attempt_count + 1" in transfer_coverage
assert "group.matched_attempt_count != group.expected_clause_count" in transfer_coverage
assert "proof_report_source_work_charge(sview_len(left.owner_name), source_work)" in transfer_key
assert "proof_report_source_work_charge(sview_len(right.owner_name), source_work)" in transfer_key
assert "proof_replay_summary_expr_equal_with_limit(left.invariant, right.invariant" in transfer_key
assert 'Ast::Stmt.Break(label, position):' in transfer_walk
assert 'Ast::Stmt.Continue(label, position):' in transfer_walk
assert transfer_walk.count('return false if label != ""') == 2
# Replay allows this phase only after matching the exact attempt/certificate transfer span;
# source admission separately binds that span and the goal to one parser-origin loop invariant.
assert 'certificate.source_phase != "" and certificate.source_phase != "loop-invariant-entry" and certificate.source_phase != "loop-invariant-preservation" and certificate.source_phase != "loop-invariant-transfer"' in replay
boundary = function_body(ROOT / "src/proof/replay/boundary_control_sources.elisa", "proof_replay_control_certificate_attempt_index_unique_with_work")
assert 'certificate.source_phase != "" and certificate.source_phase != "loop-invariant-entry" and certificate.source_phase != "loop-invariant-preservation" and certificate.source_phase != "loop-invariant-transfer"' in boundary
print("loop invariant source guard: multiplicity-aware source binding and bounded transfer replay")
