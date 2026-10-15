"""Pin fail-closed source binding for recursive-call and decreases attempts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
module = (ROOT / "src/proof/model/report_recursive_call_admission.elisa").read_text(encoding="utf-8")
attempt_index = (ROOT / "src/proof/model/report_recursive_call_attempt_index.elisa").read_text(encoding="utf-8")
structure = (ROOT / "src/proof/model/report_structure_bound_failure.elisa").read_text(encoding="utf-8")
api = (ROOT / "src/proof/replay/api.elisa").read_text(encoding="utf-8")
typed_replay = (ROOT / "src/proof/replay/typed_postcondition_replay.elisa").read_text(encoding="utf-8")
fact_trace = (ROOT / "src/proof/replay/fact_trace_validation.elisa").read_text(encoding="utf-8")

assert "proof_source_recursive_call_obligations_covered(report, source.file.top_decls, scheduled_owners, source_certificates_checked, source_work)" in structure
assert "source_certificates_checked: bool" in structure
assert "proof_source_analysis_report_structure_bound_failure(view_source, report, scheduled_owners, source_binding_complete, &source_work)" in api
assert "proof_source_analysis_report_structure_bound_failure(source, report, scheduled_owners, source_binding_complete, source_work)" in typed_replay
assert "proof_source_recursive_call_owner_scheduled(name, owner_position, scheduled_owners, scheduled_cursor, source_work)" in module
assert "scheduled_owners.push(ProofSourceScheduledOwner{name: rows[row].name, line: rows[row].line, offset: rows[row].offset})" in (ROOT / "src/proof/model/report_call_requires_census.elisa").read_text(encoding="utf-8")
assert '"source-recursive-call-obligation-coverage" if not recursive_calls_covered' in structure

substitution = "proof_substitute_with_work_limit(requires[requirement_index], parameter_names, call.arguments, source_work, PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT)"
assert substitution in module, "source substitution must share the admission meter"
substitute_at = module.index(substitution)
invalid_at = module.index("proof_replay_expr_is_invalid(expected)", substitute_at)
append_at = module.index("expected_goals.push(expected)", invalid_at)
assert substitute_at < invalid_at < append_at, "reject invalid or exhausted substitutions before inventory insertion"
assert "source_work > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT" in module[invalid_at:append_at]
assert "proof_substitute(requires[requirement_index]" not in module, "unmetered substitution must not re-enter this admission path"

assert "proof_source_recursive_call_position_hash_index(index, attempt.source_call_position" in attempt_index
assert "continue if not attempt.source_call_obligation_selected" in attempt_index
assert "proof_source_recursive_call_position_equal(index.call_positions[current], position)" in attempt_index
assert "proof_source_recursive_call_expected_goals_covered(recursive_attempt_index, expected_goals, call_index" in module
expected_coverage = attempt_index[attempt_index.index("def proof_source_recursive_call_expected_goals_covered"):]
assert "index.attempt_counts[call_index] != expected.count" not in expected_coverage, "path-specific repeated attempts must not be rejected by an exact count"
assert "slot_counts[slot] <- slot_counts[slot] - 1 if slot_counts[slot] > 0" in expected_coverage, "repeated matching attempts may not consume more than the required multiplicity"
assert "expected.count == 0 and index.attempt_counts[call_index] != 0" in expected_coverage, "empty obligations must still reject stray attempts"
assert "proof_source_recursive_call_structural_index_fill(recursive_attempt_index, report, name, owner_position, source_work)" in module
structural_index_fill_at = module.index("proof_source_recursive_call_structural_index_fill(recursive_attempt_index, report, name")
assert structural_index_fill_at < module.index("for call_index in 0..<calls.count", structural_index_fill_at), "structural certificate tables must be indexed once before per-call admission"
assert "recursive_attempt_index.structural_certificate_counts[call_index] == 1" in module
assert "proof_expr_shape_hash(expected[expected_index], 0)" in attempt_index
assert "proof_expr_shape_hash(attempt_goal, 0)" in attempt_index
assert "proof_replay_summary_expr_equal_with_limit(expected[expected_index], slot_representatives[slot]" in attempt_index
assert "proof_replay_summary_expr_equal_with_limit(attempt_goal, slot_representatives[slot]" in attempt_index
assert "slot_counts[slot] <- slot_counts[slot] + 1" in attempt_index, "duplicate source obligations must retain multiplicity"
assert "slot_counts[slot] <- slot_counts[slot] - 1" in attempt_index, "each observed attempt must consume one matching obligation"
assert "probes <= PROOF_NAME_INDEX_MAX_CLUSTER" in attempt_index, "hash collision clusters must remain bounded"
index_fill_at = module.index("proof_source_recursive_call_attempt_index_fill(recursive_attempt_index, report, calls")
per_call_at = module.index("for call_index in 0..<calls.count", index_fill_at)
assert index_fill_at < per_call_at, "attempts must be grouped once before per-call reconciliation"
assert "if not found" in expected_coverage, "attempt goals outside the reconstructed obligation set must fail"
assert "slot_counts[slot] != 0" in expected_coverage, "every reconstructed obligation must be covered"
assert "proof_source_recursive_call_measure_atom(component)" in module
assert "TokenKind.GtEq" in module and "TokenKind.Lt" in module and "TokenKind.EqEq" in module
assert "return false if unsupported_call_context" in module, "stateful surrounding statements must not bypass source substitution"
assert "proof_source_recursive_call_expr_candidate(signature_exprs[row], name, source_work)" in module, "signature clauses must not hide recursive calls from the body census"
assert "proof_source_recursive_call_structural_owner_index_build(report, source_certificates_checked, source_work)" in module
assert "proof_source_recursive_call_structural_owner_verified(structural_owners, name, source_certificates_checked, source_work)" in module
assert "structural.function_name_index_values" not in module, "source admission must not trust producer-owned structural hash slots"
assert "index.counts[row] != 1" in module, "duplicate structural rows must remain ambiguous"
assert "index.names[row] == name" in module, "hash matches must still compare exact names"
assert "total != verified.count" in module and "index.verified.push(verified[row])" in module, "the census-local structural index must validate parallel report rows"
assert "return false if not structural_owner.verified and not has_decreases" in module, "a missing structural claim must not erase recursive termination obligations"
structural_certificate_replay = fact_trace.split("def proof_replay_certificate_with_stack[", 1)[1].split("def proof_replay_certificate[", 1)[0]
source_check = "proof_replay_structural_certificate_source_valid_with_work(report, certificate, validation_workspace.source_scan_work_used, structural_cache)"
kernel_check = "proof_kernel_validate_structural_witness_shape_with_workspace"
assert source_check in structural_certificate_replay and kernel_check in structural_certificate_replay
assert structural_certificate_replay.index(source_check) < structural_certificate_replay.index(kernel_check), "structural certificate replay must bind the edge to source before kernel shape admission"
assert "proof_source_recursive_call_structural_index_fill(recursive_attempt_index, report, name, owner_position, source_work)" in module
assert "recursive_attempt_index.structural_certificate_counts[call_index] == 1" in module
assert "return false if structural_owner.verified and not structural_call_verified" in module, "every recursive edge in a structural owner needs its own replayed certificate"
assert "attempt.owner_function_line != owner_position.line or attempt.owner_function_offset != owner_position.offset" in attempt_index, "structural attempts from another declaration must be ignored"
assert "not attempt.has_certificate or not attempt.producer_proven" in attempt_index
assert "certificate.kernel_goal != attempt.kernel_goal" in attempt_index
assert "certificate_attempt_counts[attempt.certificate_index] != 0" in attempt_index, "certificate-to-attempt matching must be one-to-one"
assert "root.left != call_position.offset.usize() or certificate.line != call_position.line" in attempt_index, "structural evidence must include this exact recursive call site"
assert "for attempt in report.results.goal_attempts" in attempt_index and "for certificate_index in 0..<certificate_count" in attempt_index, "certificate reconciliation must scan each report table once per owner"
assert "proof_source_recursive_call_offset_hash_index(index, root.left, source_work)" in attempt_index
assert "index.offset_slot_hashes[slot] == hashed.hash and index.call_positions[current].offset == offset" in attempt_index
assert "proof_source_recursive_call_collect(report, declarations, declarations, declaration_names, structural_owners, scheduled_owners, &scheduled_cursor, source_certificates_checked, source_work, 0)" in module
assert "complete and scheduled_cursor == scheduled_owners.count" in module
recording = (ROOT / "src/proof/model/report_recording.elisa").read_text(encoding="utf-8")
mark_call = recording.split("def proof_mark_call_obligations_since(", 1)[1].split("\n\n", 1)[0]
assert "source_call_obligation_selected <- true" in mark_call
assert "report.results.goal_attempts.count - 1" in mark_call
assert "if not selected_position_present or selected_position_matches:" in mark_call, "outer call attribution must not steal a nested call's selected row"
invariants = (ROOT / "src/proof/model/report_invariants.elisa").read_text(encoding="utf-8")
assert "not attempt.source_call_obligation_selected" in invariants
assert "certificate.source_call_obligation_selected != attempt.source_call_obligation_selected" in invariants
replay_matcher = (ROOT / "src/proof/replay/fact_trace_validation.elisa").read_text(encoding="utf-8")
assert "attempt.source_call_obligation_selected != certificate.source_call_obligation_selected" in replay_matcher
formal_shadow_guard = module.split("continue if not recursive_scan.candidate", 1)[1].split("return false if unsupported_call_context", 1)[0]
assert "for parameter in parameters" in formal_shadow_guard
assert "parameter.name == name" in formal_shadow_guard, "formal parameters shadow declarations in the call resolver"
assert "proof_report_source_work_charge(sview_len(parameter.name), source_work)" in formal_shadow_guard
assert "PROOF_SOURCE_RECURSIVE_CALL_DEPTH_LIMIT" in module
assert "proof_report_source_work_charge(1, source_work)" in module

stmt_candidate = module[
    module.index("def proof_source_recursive_call_stmt_candidate(") :
    module.index("def proof_source_recursive_call_collect_return(")
]
for expression_statement in (
    "Ast::Stmt.Expr(expression, _):",
    "Ast::Stmt.Return(value, _):",
    "Ast::Stmt.Contract(_, expression, _):",
):
    case = stmt_candidate.split(expression_statement, 1)[1].split("\n                Ast::Stmt.", 1)[0]
    assert "candidate: bool = proof_source_recursive_call_expr_candidate(" in case
    assert "source_work <= PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT, candidate" in case

print("recursive-call admission: reconstructed obligations covered, repeated matching attempts allowed")
