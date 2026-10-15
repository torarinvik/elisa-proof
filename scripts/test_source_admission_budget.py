"""Keep termination, replay, and solver source scans inside shared work budgets."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
termination_body = (ROOT / "src/proof/check/function_termination.elisa").read_text(encoding="utf-8")
termination_expression = (ROOT / "src/proof/check/lemma_application_and_termination.elisa").read_text(encoding="utf-8")
termination_helpers = (ROOT / "src/proof/check/structural_termination_helpers.elisa").read_text(encoding="utf-8")
termination_patterns = (ROOT / "src/proof/check/termination_pattern_helpers.elisa").read_text(encoding="utf-8")
termination_contracts = (ROOT / "src/proof/check/function_contracts_and_frames.elisa").read_text(encoding="utf-8")
structural_table = (ROOT / "src/proof/model/structural_table.elisa").read_text(encoding="utf-8")
proof_api = (ROOT / "src/proof/check/api.elisa").read_text(encoding="utf-8")
checked_view = (ROOT / "src/proof/model/checked_view.elisa").read_text(encoding="utf-8")
theorem_source_admission = (ROOT / "src/proof/model/report_theorem_source_admission.elisa").read_text(encoding="utf-8")
structural_name_index = (ROOT / "src/proof/check/structural_name_index.elisa").read_text(encoding="utf-8")
structural_replay_source = (ROOT / "src/proof/replay/structural_source_validation.elisa").read_text(encoding="utf-8")
structural_replay_cache = (ROOT / "src/proof/replay/structural_source_cache_validation.elisa").read_text(encoding="utf-8")
output_helpers = (ROOT / "src/app/report_output_integrated_helpers.elisa").read_text(encoding="utf-8")
cli_source = (ROOT / "src/app/cli.elisa").read_text(encoding="utf-8")
theorem_suggestions = (ROOT / "src/app/theorem_output_suggestions.elisa").read_text(encoding="utf-8")
goal_admission = (ROOT / "src/proof/model/report_goal_admission.elisa").read_text(encoding="utf-8")
postcondition_inventory = (ROOT / "src/proof/model/report_postcondition_ast_inventory.elisa").read_text(encoding="utf-8")
type_bound_local = (ROOT / "src/proof/replay/type_bound_local_availability.elisa").read_text(encoding="utf-8")
linear_goal_api = (ROOT / "src/proof/linear/goal_api.elisa").read_text(encoding="utf-8")
kernel_resource_model = (ROOT / "src/proof/kernel_replay/resource_model.elisa").read_text(encoding="utf-8") + (ROOT / "src/proof/kernel_replay/resource_model_depth.elisa").read_text(encoding="utf-8")
return_matches = (ROOT / "src/proof/check/returns/matches.elisa").read_text(encoding="utf-8")
assert "source_work: mutable usize&" in termination_body.splitlines()[2]
assert "proof_replay_summary_expr_cost_body(body, &body_cost, source_work, 0)" in termination_body
assert "body_cost > (PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT - source_work) / 4" in termination_body
assert "proof_report_source_work_charge(body_cost * 4, source_work)" in termination_body
body_preflight = termination_body.split("body_cost: mutable usize = 0", 1)[1].split("if not extern_contract_summary_complete", 1)[0]
for failure_branch in body_preflight.split("if not proof_replay_summary_expr_cost_body(body, &body_cost, source_work, 0):", 1)[1].split("if not proof_report_source_work_charge(body_cost * 4, source_work):", 1):
    assert "return" in failure_branch
assert body_preflight.count("proof_structural_source_work_exhaust(source_work)") == 2
assert "proof_report_source_work_charge(body_cost * 4, source_work)" in body_preflight
assert "termination traversal itself charges each node" in termination_body
body_walk = termination_body.split("def proof_structural_check_body(", 1)[1].split("def proof_structural_signature_contract_table_valid", 1)[0]
assert "proof_replay_summary_expr_cost_body(" not in body_walk, "nested body visits must not rescan every descendant subtree"
assert "proof_structural_environment_work_charge(parameters, current_destructurable, current_smaller, source_work, true)" in termination_body
assert "proof_structural_environment_work_charge(parameters, destructurable, smaller, source_work, false)" in termination_expression
assert "proof_report_source_work_charge(1, source_work)" in termination_expression
for compared_text in ("finding.kind", "finding.name", "finding.message"):
    assert f"proof_report_source_work_charge(sview_len({compared_text}), source_work)" in termination_body
assert "proof_structural_termination_finding(report, declaration_line, function_name, \"structural finding scan exceeded its validated bound\")" in termination_body
body_match = termination_body.split("Ast::Stmt.Match(scrutinee, arms, position):", 1)[1].split("Ast::Stmt.Block(", 1)[0]
assert "arm_pattern_complete: bool = proof_structural_pattern_bindings" in body_match
assert "if not arm_pattern_complete:" in body_match
assert "pattern binding analysis exceeded its validated bound" in body_match
assert "if not arm_destructurable_complete or not arm_subterms_complete:" in body_match
assert "pattern subterm analysis exceeded its validated bound" in body_match
expression_match = termination_expression.split("Ast::Expr.Match(scrutinee, arms, _):", 1)[1].split("Ast::Expr.Catch(", 1)[0]
assert "if not arm_pattern_complete:" in expression_match
assert "match pattern binding analysis exceeded its validated bound" in expression_match
assert "if not arm_destructurable_complete or not arm_subterms_complete:" in expression_match
assert "match pattern subterm analysis exceeded its validated bound" in expression_match
expression_catch = termination_expression.split("Ast::Expr.Catch(", 1)[1].split("Ast::Expr.GetElse(", 1)[0]
assert "if not arm_pattern_complete:" in expression_catch
assert "catch pattern binding analysis exceeded its validated bound" in expression_catch
assert "report.proof_obligation(false) if not arm_pattern_complete" not in termination_expression
return_pattern_walk = return_matches.split("pattern_bindings: mutable darray[sview] = []", 1)[1].split("proof_remove_type_bound_facts_for_names", 1)[0]
assert "pattern_bindings_complete: bool = proof_structural_pattern_bindings" in return_pattern_walk
assert "pattern_supported <- false if not pattern_bindings_complete" in return_pattern_walk
assert "Every arm consumes the function-wide return-step budget above" in return_pattern_walk
for helper in (
    "proof_structural_pattern_bindings_with_source_work",
    "proof_structural_pattern_subterms_with_source_work",
):
    assert f"def {helper}(" in termination_patterns
assert "proof_structural_pattern_source_work_charge(1, source_work, source_limit)" in termination_patterns
assert "source_work <- source_limit + 1" in termination_patterns
assert "report, 0, false, &work, source_work, source_limit" in termination_patterns
assert "if strict_context and name != \"\"" in termination_patterns
assert "Ast::Pattern.TypeBind(_, binder):" in termination_patterns
assert "if strict_context and binder != \"\"" in termination_patterns
assert "Ast::Pattern.As(name, inner):" in termination_patterns
assert "proof_structural_pattern_bindings_with_source_limit(arm.pattern, &pattern_bindings, pattern_source_work, PROOF_PURITY_WALK_WORK_LIMIT)" in return_matches
assert "report.analysis_1.budgets.return_source_work <- pattern_source_work" in return_matches
assert "proof_structural_pattern_bindings_with_source_work(arm.pattern, &arm_bindings, source_work)" in body_match
assert "proof_structural_pattern_subterms_with_source_work(arm.pattern" in body_match
assert "proof_structural_pattern_bindings_with_source_work(arm.pattern, &arm_bindings, source_work)" in expression_match
assert "proof_structural_pattern_subterms_with_source_work(arm.pattern" in expression_match
assert "proof_structural_pattern_bindings_with_source_work(arm.pattern, &arm_bindings, source_work)" in expression_catch
argument_root_walk = termination_helpers.split("def proof_structural_argument_root_with_work(", 1)[1].split("def proof_structural_argument_metadata(", 1)[0]
assert "PROOF_PATTERN_WALK_DEPTH_LIMIT" in argument_root_walk
assert "proof_report_source_work_charge(1, source_work)" in argument_root_walk
argument_metadata = termination_helpers.split("def proof_structural_argument_metadata(", 1)[1].split("def proof_structural_binding_identity_with_work(", 1)[0]
assert "proof_structural_argument_root_with_work(expression, source_work, 0)" in argument_metadata
assert "proof_report_source_work_charge(sview_len(candidate.name), source_work)" in argument_metadata
assert "candidate.subject == requested_subject" in argument_metadata
assert "candidate.identity, candidate.subject_identity" in argument_metadata
assert "proof_structural_argument_metadata(recursive_argument, smaller, subject, source_work)" in termination_expression
assert "proof_structural_argument_metadata(recursive_argument, smaller, \"\", source_work)" in termination_expression
assert "proof_structural_argument_metadata(iterable, current_smaller, \"\", source_work)" in termination_body
assert "proof_structural_smaller_has_name_with_work(loop_smaller, loop_variable, source_work)" in termination_body
assert "structural loop subterm lookup exceeded its validated bound" in termination_body
assert "verified_members: mutable darray[bool] = []" in structural_table
assert "report.analysis_1.structural.verified_members.push(false)" in termination_body
verified_publication = termination_body.split("if not structural_failed:", 1)[1].split("def proof_check_structural_termination(", 1)[0]
assert "proof_structural_verified_member_publish(report, own_lookup.row, function_name, source_work)" in verified_publication
verified_member_publish = termination_helpers.split("def proof_structural_verified_member_publish(", 1)[1].split("def proof_structural_environment_work_charge(", 1)[0]
assert "row >= report.analysis_1.structural.verified_members.count" in verified_member_publish
assert "proof_report_source_work_charge(2, source_work)" in verified_member_publish
assert "report.analysis_1.structural.verified_names.push(name)" in verified_member_publish
assert "report.analysis_1.structural.verified_members[row] <- true" in verified_member_publish
structural_summary = termination_contracts.split("structural_summary: mutable bool = false", 1)[1].split("structural_failure:", 1)[0]
assert "verified_members.count == report.analysis_1.structural.names.count" in structural_summary
assert "verified_members[caller_index]" in structural_summary and "verified_members[function_index]" in structural_summary
assert "proof_structural_name_in(report.analysis_1.structural.verified_names" not in termination_contracts
assert "report.analysis_1.structural.verified_members.clear()" in proof_api
diagnostic_counting = checked_view.split("def proof_semantic_diagnostic_counts_with_work(", 1)[1].split("def proof_source_analysis_refines_function(", 1)[0]
assert "proof_structural_verified_member_lookup_with_work(report, diagnostic.name, source_work)" in diagnostic_counting
assert "if not verified_member.complete:" in diagnostic_counting
assert "for verified_name in report.analysis_1.structural.verified_names" not in diagnostic_counting
verified_member_lookup = structural_name_index.split("def proof_structural_verified_member_lookup_with_work(", 1)[1]
assert "structural.verified_members.count != name_count" in verified_member_lookup
assert "proof_replay_source_work_charge(sview_len(wanted), source_work)" in verified_member_lookup
assert "structural.function_name_index_ambiguous[slot]" in verified_member_lookup
assert "return (true, false) if structural.function_name_index_ambiguous[slot]" in verified_member_lookup
assert "for duplicate_row in 0..<name_count" not in verified_member_lookup
assert "return (false, false, name_count) if report.analysis_1.structural.function_name_index_ambiguous[slot]" in structural_name_index
assert structural_name_index.count("verified_members[row] <- true") == 0
assert "report.analysis_1.structural.verified_members[row] <- true" in termination_helpers
assert "report.analysis_1.structural.verified_members.push(false)" in structural_replay_source
replay_verified_reset = structural_replay_cache.split("cache.scratch.analysis_1.structural.verified_names.clear()", 1)[1].split("proof_check_structural_function(", 1)[0]
assert "verified_members.count != cache.scratch.analysis_1.structural.names.count" in replay_verified_reset
assert "for verified_row in 0..<cache.scratch.analysis_1.structural.verified_members.count" in replay_verified_reset
assert "proof_replay_structural_work_charge(source_work, 1)" in replay_verified_reset
assert "cache.scratch.analysis_1.structural.verified_members[verified_row] <- false" in replay_verified_reset
replay_owner_check = structural_replay_cache.split("def proof_replay_structural_certificate_source_valid_with_work(", 1)[1]
assert "caller_node >= cache.scratch.analysis_1.structural.verified_members.count" in replay_owner_check
assert "verified_members.count != cache.graph.nodes.declarations.count" in replay_owner_check
assert "proof_replay_structural_work_charge(source_work, 1)" in replay_owner_check
assert "cache.scratch.analysis_1.structural.verified_members[caller_node]" in replay_owner_check
assert "for verified_name in cache.scratch.analysis_1.structural.verified_names" not in replay_owner_check
assert "proof_semantic_diagnostic_visibility_snapshot_with_work" in output_helpers
visibility_snapshot = output_helpers.split("def proof_semantic_diagnostic_visibility_snapshot_with_work(", 1)[1].split("def proof_report_discharges_return(", 1)[0]
assert "proof_output_reserve_status_snapshot_work(source_work, diagnostics.count)" in visibility_snapshot
assert "proof_structural_verified_member_lookup_with_work(report, diagnostic.name, source_work)" in visibility_snapshot
assert "return (false, []) if not verified_member.complete" in visibility_snapshot
assert "any verified_name in report.analysis_1.structural.verified_names" not in output_helpers
assert "continue if semantic_visibility_snapshot.complete and not semantic_visibility[diagnostic_index]" in output_helpers
assert "semantic_diagnostics_complete\\\":true" in output_helpers and "semantic_diagnostics_complete\\\":false" in output_helpers
full_json_output = output_helpers.split("def proof_push_json_report_with_replay[@view", 1)[1]
assert "semantic_visibility_snapshot.complete" in full_json_output.split("\n    status_snapshot_complete: bool =", 1)[1].split("\n", 1)[0]
assert "continue if semantic_visibility_snapshot.complete and not semantic_visibility[diagnostic_index]" in cli_source
assert "unknown (visibility work limit)" in cli_source
assert "text_status_snapshot_complete: bool =" in cli_source and "semantic_visibility_snapshot.complete" in cli_source.split("text_status_snapshot_complete: bool =", 1)[1].split("\n", 1)[0]
assert "proof_semantic_diagnostic_visible(" not in output_helpers and "proof_semantic_diagnostic_visible(" not in cli_source
suggestion_body = theorem_suggestions.split("def proof_push_json_suggestions_with_replayed[", 1)[1]
outer_theorem_loop = suggestion_body.split("for theorem_index in 0..<report.analysis_1.theorems.summaries.count", 1)[1].split("valid_parameters:", 1)[0]
assert "proof_suggestion_work_charge(replay_work, 1)" in outer_theorem_loop
assert "proof_checked_view_theorem_source_admission_with_work(checked_view, theorem_index, &replay_work)" in suggestion_body
assert "theorem_source_status.source_admissible and theorem_source_status.declaration_identity_unambiguous" in suggestion_body
assert "proof_declaration_name_is_unique" not in suggestion_body
assert "proof_checked_view_theorem_source_admissions_complete(checked_view)" in suggestion_body
assert "goal_facts_source_admissible: bool = goal_status_parts_complete and goal_id < report.results.goal_attempts.count and goal_status_parts.facts_source_admitted" in suggestion_body
assert 'proof_push(buffer, "true" if goal_facts_source_admissible else "false")' in suggestion_body
assert "and goal_source_admissible and goal_facts_source_admissible:" in suggestion_body
assert "if goal_id < report.results.goal_attempts.count and goal_source_admissible and goal_facts_source_admissible:" in suggestion_body
identity_status = theorem_source_admission.split("def proof_report_declaration_identity_statuses(", 1)[1].split("private:", 1)[0]
assert 'if declaration.kind == "lemma":' in identity_status
assert 'if declaration.kind in {"function", "lemma"}:' not in identity_status
identity_index_builder = theorem_source_admission.split("def proof_report_declaration_name_multiplicity_index(", 1)[1].split("def proof_report_declaration_name_is_unique(", 1)[0]
assert 'declarations <- declarations + 1 if declaration.kind == "lemma"' in identity_index_builder
assert 'continue if declaration.kind != "lemma"' in identity_index_builder
declaration_gap_body = (ROOT / "src/app/theorem_output.elisa").read_text(encoding="utf-8").split("def proof_push_json_declaration[", 1)[1].split("def proof_push_json_theorem(", 1)[0]
assert "if declaration.verified and source_clean and source_admissions_complete and (not declaration.lemma or declaration_identity_unambiguous):" in declaration_gap_body
assert "declaration_gaps <- proof_declaration_gap_index_find(gap_index, declaration.name, declaration.line, declaration.source_offset, replay_work)" in declaration_gap_body
assert "declaration-identity-unavailable" in declaration_gap_body
assert "(not declaration.lemma or declaration_identity_unambiguous) and declaration_gaps.complete" in declaration_gap_body
assert 'proof_push(buffer, "true" if declaration.verified and source_clean and source_admissions_complete and (not declaration.lemma or declaration_identity_unambiguous) and declaration_gaps.complete and declaration_gaps.found and not replay_gap and not source_gap else "false")' in declaration_gap_body
assert "proof_declaration_gap_index_build(checked_view, report, replay_work)" in declaration_gap_body
assert "proof_declaration_gap_index_find(gap_index, declaration.name, declaration.line, declaration.source_offset, replay_work)" in declaration_gap_body
assert "declaration_gap_index_built: mutable bool = false" in (ROOT / "src/app/theorem_output.elisa").read_text(encoding="utf-8")
gap_index_source = (ROOT / "src/app/theorem_output.elisa").read_text(encoding="utf-8")
gap_index_record = gap_index_source.split("def proof_declaration_gap_index_record(", 1)[1].split("def proof_declaration_gap_index_build", 1)[0]
gap_index_build = gap_index_source.split("def proof_declaration_gap_index_build[", 1)[1].split("def proof_declaration_gap_index_find(", 1)[0]
gap_index_find = (ROOT / "src/app/theorem_output.elisa").read_text(encoding="utf-8").split("def proof_declaration_gap_index_find(", 1)[1].split("def proof_theorem_has_replay_gap[", 1)[0]
assert "for goal_id in 0..<attempt_count" in gap_index_build
assert "attempt_count > limit or theorem_count > limit - attempt_count or declaration_count > limit - attempt_count - theorem_count" in gap_index_build
assert "not proof_output_reserve_status_snapshot_work(work, 4 + sview_len(attempt.name))" in gap_index_build
assert "replay_gap: bool = not status.producer_claim or not status.replayed" in gap_index_build
assert "theorem_count: usize = report.analysis_1.theorems.summaries.count" in gap_index_build
assert "declaration_count: usize = report.analysis_1.declaration_details.count" in gap_index_build
assert "indexed_rows: usize = attempt_count + theorem_count + declaration_count" in gap_index_build
assert "target_capacity: usize = indexed_rows * 2" in gap_index_build
assert "proof_checked_view_attempt_status_snapshot_with_work(checked_view, goal_id, work)" in gap_index_build
assert "source_gap: bool = not status.source_admitted" in gap_index_build
assert "index.replay_gaps[current] <- index.replay_gaps[current] or replay_gap" in gap_index_record
assert "index.source_gaps[current] <- index.source_gaps[current] or source_gap" in gap_index_record
assert "proof_output_text_equal_with_work(index.names[current], name, work)" in gap_index_record
assert "proof_output_text_equal_with_work(index.names[current], name, work)" in gap_index_find
assert "PROOF_DECLARATION_GAP_INDEX_MAX_CLUSTER" in gap_index_record and "PROOF_DECLARATION_GAP_INDEX_MAX_CLUSTER" in gap_index_find
assert "work_used <- limit + 1" in (ROOT / "src/app/output_replay_status.elisa").read_text(encoding="utf-8").split("def proof_output_reserve_status_snapshot_work(", 1)[1].split("def proof_output_checked_view_goal_statuses_with_work", 1)[0]
assert "work <- limit + 1" in gap_index_build
assert "work <- ElisaProof::proof_replay_summary_source_work_limit() + 1" in gap_index_find
assert "if not proof_declaration_gap_index_record(index," in gap_index_build and "work <- limit + 1" in gap_index_build
assert '"output-work-limit" if replay_work > ElisaProof::proof_replay_summary_source_work_limit() else "declaration-gap-index-incomplete"' in declaration_gap_body
assert "proof_goal_fingerprint_with_limit(report, report.results.goal_attempts[goal_id], replay_work, ElisaProof::proof_replay_summary_source_work_limit())" in suggestion_body
assert "suggestions_complete <- false if replay_work > ElisaProof::proof_replay_summary_source_work_limit()" in suggestion_body
assert "proof_goal_fingerprint(report, report.results.goal_attempts[goal_id])" not in suggestion_body
unsafe_source_shape = goal_admission.split("def proof_report_postcondition_has_unsafe_source_shape_depth(", 1)[1].split("# Find unqualified result variables", 1)[0]
assert "Ast::Expr.Absent |" not in unsafe_source_shape
assert "proof_report_source_work_charge(1, source_work)" in unsafe_source_shape
assert "proof_report_source_work_charge(sview_len(name), source_work)" in unsafe_source_shape
assert "for element in elements |source_work|" in unsafe_source_shape
assert "for entry in entries |source_work|" in unsafe_source_shape
assert "for arm in arms |source_work|" in unsafe_source_shape
assert "for statement in statements |value_checks_result, value_checks_old, source_work|" in unsafe_source_shape
assert "arm.guard != Ast::Expr.Absent and proof_report_postcondition_has_unsafe_source_shape_depth(arm.guard" in unsafe_source_shape
unsafe_match = unsafe_source_shape.split("Ast::Expr.Match(scrutinee, arms, position):", 1)[1].split("Ast::Expr.Comprehension", 1)[0]
assert unsafe_match.index("arm.body.count != 1") < unsafe_match.index("proof_report_postcondition_has_unsafe_source_shape_depth(arm.guard")
result_reference_match = goal_admission.split("def proof_report_postcondition_source_scan_depth(", 1)[1].split("def proof_report_postcondition_return_lookup(", 1)[0].split("Ast::Expr.Match(scrutinee, arms, position):", 1)[1].split("Ast::Expr.GetElse", 1)[0]
assert result_reference_match.index("arm.body.count != 1") < result_reference_match.index("proof_report_postcondition_source_scan_depth(arm.guard")
pattern_binder_budget = goal_admission.split("def proof_report_postcondition_pattern_special_binders(", 1)[1].split("def proof_report_postcondition_match_binder_visibility(", 1)[0]
for charged_text in ('sview_len(name)', 'sview_len("result")', 'sview_len("old")'):
    assert f"proof_report_source_work_charge({charged_text}, source_work)" in pattern_binder_budget
result_consumer = type_bound_local.split("def proof_replay_type_bound_result_consumer_matches(", 1)[1].split(
    "# Later straight-line locals are harmless", 1
)[0]
assert "Ast::Stmt.Return(expression, position):" in result_consumer
assert "proof_replay_type_bound_equal_span_return_valid(returned, return_position, work)" in result_consumer
assert "return_position.line != returned_position.line" in result_consumer
assert "return_position.offset >= returned_position.offset" in result_consumer
assert "return_position.end_offset > returned_position.offset" in result_consumer
assert "return_position.offset > return_position.end_offset" in result_consumer
assert "proof_replay_source_position_equal(returned_position, return_position)" in result_consumer
equal_span_return = type_bound_local.split("def proof_replay_type_bound_equal_span_return_valid(", 1)[1].split(
    "def proof_replay_type_bound_result_consumer_matches(", 1
)[0]
for parser_owned_check in (
    "proof_replay_source_position_equal(if_position, return_position)",
    "proof_replay_type_bound_local_work_charge(4, work)",
    "proof_replay_type_bound_position_after_extent(Ast::expr_pos(condition), return_extent)",
    "proof_replay_type_bound_position_after_extent(Ast::expr_pos(then_expression), return_extent)",
    "proof_replay_type_bound_position_after_extent(Ast::expr_pos(else_expression), return_extent)",
):
    assert parser_owned_check in equal_span_return
assert "proof_source_kernel_collect_type_index(declarations" in postcondition_inventory
assert "proof_source_kernel_type_sort(declared_return_type" in postcondition_inventory
assert 'return_sort.sort == "void"' in postcondition_inventory
assert "not return_sort.known or return_sort.sort == \"void\"" in postcondition_inventory
runtime_fingerprint = (ROOT / "src/app/runtime.elisa").read_text(encoding="utf-8")
fingerprint_limit_body = runtime_fingerprint.split("def proof_goal_fingerprint_with_limit(", 1)[1].split("def proof_theorem_identity_work_charge(", 1)[0]
fingerprint_preflight = runtime_fingerprint.split("def proof_goal_identity_work_preflight(", 1)[1].split("def proof_goal_fingerprint(", 1)[0]
assert "work_limit: usize" in runtime_fingerprint.split("def proof_goal_fingerprint_with_limit(", 1)[1].split("\n", 1)[0]
assert "work > work_limit" in fingerprint_preflight
assert "work_limit - work" in fingerprint_preflight
assert "PROOF_JSON_EXPRESSION_WORK_LIMIT + 1" not in fingerprint_limit_body
assert "identity_bytes, 0, PROOF_JSON_EXPRESSION_WORK_LIMIT" in runtime_fingerprint
parameter_identity = termination_helpers.split("def proof_structural_parameter_identity_with_work(", 1)[1].split("def proof_structural_call_argument(", 1)[0]
assert "proof_report_source_work_charge(sview_len(parameter_name), source_work)" in parameter_identity
assert "proof_report_source_work_charge(sview_len(wanted), source_work)" in parameter_identity
enum_subjects = termination_helpers.split("def proof_enum_parameter_names_from_parameters(", 1)[1].split("def proof_structural_report_same_component(", 1)[0]
assert "source_work: mutable usize&" in enum_subjects
assert "proof_report_source_work_charge(sview_len(candidate), source_work)" in enum_subjects
assert "recursive subject enumeration exceeded its validated bound" in termination_expression
for stale_helper in (
    "proof_structural_argument_root(",
    "proof_structural_argument_is_smaller(",
    "proof_structural_argument_subject(",
    "proof_structural_argument_identity(",
    "proof_structural_parameter_identity(",
):
    assert stale_helper not in termination_helpers + termination_body + termination_expression
argument_mapping = termination_helpers.split("def proof_structural_call_argument(", 1)[1].split("def proof_parameter_position(", 1)[0]
assert "source_work: mutable usize&" in argument_mapping
assert "for argument_index in 0..<argument_names.count" in argument_mapping
assert "proof_report_source_work_charge(sview_len(label), source_work)" in argument_mapping
assert "proof_report_source_work_charge(sview_len(target_name), source_work)" in argument_mapping
assert "return (false, Ast::Expr.Invalid)" in argument_mapping
named_argument_scan = termination_helpers.split("def proof_structural_call_has_named_argument(", 1)[1].split("def proof_parameter_position(", 1)[0]
assert "source_work: mutable usize&" in named_argument_scan
assert "proof_report_source_work_charge(sview_len(label), source_work)" in named_argument_scan
parameter_position = termination_helpers.split("def proof_parameter_position(", 1)[1].split("def proof_enum_parameter_names_from_parameters(", 1)[0]
assert "source_work: mutable usize&" in parameter_position
assert "proof_report_source_work_charge(sview_len(parameter_name), source_work)" in parameter_position
assert "proof_report_source_work_charge(sview_len(wanted), source_work)" in parameter_position
assert "recursive call argument mapping exceeded its validated bound" in termination_expression
assert "recursive subject lookup exceeded its validated bound" in termination_expression
assert "proof_structural_call_argument(arguments, argument_names, parameters, subject_index, source_work)" in termination_expression
assert "proof_structural_call_argument(arguments, argument_names, parameters, recursive_position, source_work)" in termination_expression
assert "proof_structural_call_has_named_argument(argument_names, source_work) if mutual_recursive" in termination_expression
assert "recursive call argument-label scan exceeded its validated bound" in termination_expression
assert "environment_count * environment_count" in termination_helpers
assert "source_work <- PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT + 1" in termination_helpers
assert "proof_structural_source_work_exhaust(source_work) if not proof_report_source_work_charge(1, source_work)" in termination_helpers
assert "def proof_structural_environment_join_work_charge(" in termination_helpers
assert "proof_structural_environment_join_work_charge(current_destructurable, current_smaller, arm_destructurable, arm_smaller, source_work)" in termination_body
assert "proof_structural_environment_join_work_charge(current_destructurable, current_smaller, loop_destructurable, loop_smaller, source_work)" in termination_body
join_work = termination_helpers.split("def proof_structural_environment_join_work_charge(", 1)[1].split("def proof_structural_name_in(", 1)[0]
assert "proof_structural_environment_metrics(left_destructurable, left_smaller, source_work)" in join_work
assert "proof_structural_environment_metrics(right_destructurable, right_smaller, source_work)" in join_work
assert "proof_structural_source_work_product_charge(left.destructurable_count, right.destructurable_count, source_work)" in join_work
assert "proof_structural_source_work_product_charge(left.smaller_count, right.smaller_count, source_work)" in join_work
for category in ("destructurable_name_bytes", "smaller_name_bytes"):
    assert f"proof_structural_source_work_product_charge(right.{category.split('_')[0]}_count, left.{category}, source_work)" in join_work
    assert f"proof_structural_source_work_product_charge(left.{category.split('_')[0]}_count, right.{category}, source_work)" in join_work
assert "proof_structural_source_work_product_charge(right.smaller_count, left.smaller_subject_bytes, source_work)" in join_work
assert "proof_structural_source_work_product_charge(left.smaller_count, right.smaller_subject_bytes, source_work)" in join_work
assert "structural match join work exceeded its validated bound" in termination_body
assert "structural branch join work exceeded its validated bound" in termination_body
capture_overlap = termination_helpers.split("def proof_structural_captures_overlap(", 1)[1].split("def proof_structural_without(", 1)[0]
assert "source_work: mutable usize&" in capture_overlap
assert "proof_report_source_work_charge(sview_len(capture), source_work)" in capture_overlap
assert "proof_report_source_work_charge(sview_len(candidate.name), source_work)" in capture_overlap
assert "proof_report_source_work_charge(sview_len(capture), source_work) or not proof_report_source_work_charge(sview_len(candidate.name), source_work)" in capture_overlap
block_capture = termination_expression.split("Ast::Expr.Block(statements, value, captures, _):", 1)[1].split("Ast::Expr.Lambda(", 1)[0]
assert "proof_replay_summary_expr_repeat_charge_with_work(expression, 1, source_work)" in block_capture
assert "proof_structural_captures_overlap(captures, block_smaller, source_work)" in block_capture
assert "captured value block overlap analysis exceeded its validated bound" in block_capture
assert "proof_structural_source_work_exhaust(source_work)" in termination_body
for loop_label in (
    "structural call argument work exceeded its validated bound",
    "structural index argument work exceeded its validated bound",
    "structural collection work exceeded its validated bound",
    "structural dictionary work exceeded its validated bound",
    "structural match arm work exceeded its validated bound",
    "structural catch arm work exceeded its validated bound",
):
    assert loop_label in termination_expression
environment_charge = termination_helpers.split("def proof_structural_environment_work_charge(", 1)[1].split("\n        def ", 1)[0]
for index, line in enumerate(environment_charge.splitlines()):
    if line.lstrip().startswith("for "):
        indent = len(line) - len(line.lstrip())
        body_end = index + 1
        lines = environment_charge.splitlines()
        while body_end < len(lines):
            candidate = lines[body_end]
            if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                break
            body_end += 1
        if any("source_work" in row for row in lines[index + 1:body_end]):
            captures = line.strip().split("|", 2)[1]
            assert "source_work" in [item.strip() for item in captures.split(",")], line
for source in (termination_body, termination_expression, termination_helpers):
    source_lines = source.splitlines()
    for index, line in enumerate(source_lines):
        if "proof_structural_check_body(" in line or "proof_structural_check_expression(" in line:
            if line.lstrip().startswith("def "):
                continue
            assert line.rstrip().endswith(", source_work)") or ", source_work) if " in line, line
        stripped = line.lstrip()
        if stripped.startswith("for ") and "|" in stripped and stripped.endswith("|:"):
            indent = len(line) - len(stripped)
            end = index + 1
            while end < len(source_lines):
                candidate = source_lines[end]
                if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                    break
                end += 1
            if any("proof_structural_check_body(" in row or "proof_structural_check_expression(" in row for row in source_lines[index + 1:end]):
                captures = stripped.split("|", 2)[1]
                assert "source_work" in [item.strip() for item in captures.split(",")], line
pattern_lines = termination_patterns.splitlines()
for index, line in enumerate(pattern_lines):
    stripped = line.lstrip()
    if not stripped.startswith("for ") or "|" not in stripped or not stripped.endswith("|:"):
        continue
    indent = len(line) - len(stripped)
    end = index + 1
    while end < len(pattern_lines):
        candidate = pattern_lines[end]
        if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
            break
        end += 1
    if any("proof_structural_pattern_" in row and "_with_budget(" in row for row in pattern_lines[index + 1:end]):
        captures = stripped.split("|", 2)[1]
        assert "source_work" in [item.strip() for item in captures.split(",")], line
        assert "source_limit" in [item.strip() for item in captures.split(",")], line

declaration_recording = (ROOT / "src/proof/check/declaration_recording.elisa").read_text(encoding="utf-8")
function_index = (ROOT / "src/proof/check/function_index.elisa").read_text(encoding="utf-8")
lemma_identity = (ROOT / "src/proof/check/verification_findings.elisa").read_text(encoding="utf-8")
assert "proof_lemma_source_row_with_work(lemmas, name, position.line, position.offset, source_work)" in declaration_recording
assert "proof_lemma_source_row_with_work(lemmas, name, position.line, position.offset, source_work)" in function_index
assert "lemmas.identity.offsets[lookup.index] == offset" in lemma_identity
assert "lemmas.identity.lines[index] == line and lemmas.identity.offsets[index] == offset" in lemma_identity
assert '"goal-owner-unavailable"' in declaration_recording
assert "proof_declaration_attempt_index_build(report, source_work)" in declaration_recording
assert "proof_declaration_attempt_index_find(attempt_index, name, position.line, position.offset, source_work)" in declaration_recording
assert "attempt.owner_function_line" in declaration_recording and "attempt.owner_function_offset" in declaration_recording
report_model = (ROOT / "src/proof/model.elisa").read_text(encoding="utf-8")
assert "owner_function_line: u32 = 0" in report_model
assert "owner_function_offset: u32 = 0" in report_model
owner_scope = (ROOT / "src/proof/check/function_checks.elisa").read_text(encoding="utf-8").split("def proof_check_function_with_goal_owner(", 1)[1].split("def proof_check_function(", 1)[0]
assert "report.context.current_goal_owner_line <- position.line" in owner_scope
assert "report.context.current_goal_owner_offset <- position.offset" in owner_scope
assert "report.context.current_goal_owner_line <- saved_line" in owner_scope
assert "report.context.current_goal_owner_offset <- saved_offset" in owner_scope
source_work_charge = (ROOT / "src/proof/model/report_theorem_source_admission.elisa").read_text(encoding="utf-8").split("def proof_report_source_work_charge(", 1)[1].split("def ", 1)[0]
assert "work <- PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT + 1" in source_work_charge
assert "if name_index_work > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT:" in (ROOT / "src/proof/check/api.elisa").read_text(encoding="utf-8").split("proof_record_declarations(file", 1)[1]
direct_api_admission = (ROOT / "scripts/test_direct_api_semantic_admission.py").read_text(encoding="utf-8")
assert 'expected_kind: sview = "semantic-source-inadmissible" if index < 3 else ("semantic-permission-ungranted" if index >= 7 else "arithmetic-safety-refuted")' in direct_api_admission

# Equality meters both expression trees into one aggregate cost before reserving the
# comparison pass. Keep the shared caller meter charged for both traversals.
summary_cost = (ROOT / "src/proof/replay/summary_source_cost.elisa").read_text(encoding="utf-8")
equal_helper = summary_cost.split("def proof_replay_summary_expr_equal_with_limit(", 1)[1].split(
    "def proof_replay_summary_expr_proof_equal_with_limit(", 1
)[0]
assert "left_cost: mutable usize = 0" in equal_helper
assert "right_cost: mutable usize = 0" in equal_helper
assert "proof_replay_summary_expr_cost_with_limit(left, &left_cost, work, work_limit)" in equal_helper
assert "right_work: usize = work + left_cost" in equal_helper
assert "proof_replay_summary_expr_cost_with_limit(right, &right_cost, right_work, work_limit)" in equal_helper
assert "combined_cost: usize = left_cost + right_cost" in equal_helper
assert "combined_cost > remaining / 2" in equal_helper
assert "work <- work + combined_cost * 2" in equal_helper
assert "proof_replay_expr_equal_depth(left, right, 0)" in equal_helper

# Source goal shortcuts must use the shared witness index and meter recursive primitive
# comparisons before they can establish disequality or unsigned reflexivity.
goal_shortcuts = (ROOT / "src/proof/linear/disequality_goal_work.elisa").read_text(encoding="utf-8")
strict_progress_work = (ROOT / "src/proof/linear/strict_progress_work.elisa").read_text(encoding="utf-8")
disequality = goal_shortcuts.split("def proof_scalar_disequality_goal_with_work(", 1)[1].split(
    "def proof_unsigned_goal_identity_with_work(", 1
)[0]
assert "proof_scalar_witness_markers_with_work(facts, true, budget, exhausted)" in disequality
assert "proof_linear_safety_marker_scale_with_work(markers.witnesses, budget, exhausted)" in disequality
assert "proof_linear_search_expr_equal_with_work" in disequality
literal_term = goal_shortcuts.split("def proof_disequality_literal_term_with_work(", 1)[1].split(
    "def proof_signed_disequality_literal_with_work(", 1
)[0]
assert "proof_linear_safety_comparison_with_work" in literal_term
equality_scan = goal_shortcuts.split("def proof_disequality_from_equality_with_work(", 1)[1].split(
    "def proof_unsigned_goal_identity_with_work(", 1
)[0]
assert "proof_linear_safety_comparison_with_work" in equality_scan
for legacy in (
    "proof_signed_disequality_from_equality_fact(goal, facts)",
    "proof_signed_distinct_disequality_disjunction(goal, facts)",
    "proof_unsigned_disequality_from_equality_fact(goal, facts)",
    "proof_unsigned_distinct_disequality_disjunction(goal, facts)",
):
    assert legacy not in disequality
unsigned_identity = goal_shortcuts.split("def proof_unsigned_goal_identity_with_work(", 1)[1].split(
    "def proof_signed_product_growth_with_work(", 1
)[0]
assert "proof_linear_safety_comparison_with_work" in unsigned_identity
assert "proof_linear_safety_work_charge_product4_with_work" in unsigned_identity
assert "proof_unsigned_goal_identity(goal, facts)" not in unsigned_identity
legacy_shape_adapter = goal_shortcuts.split("def proof_unsigned_legacy_goal_shapes_with_work(", 1)[1].split(
    "def proof_signed_product_factor_with_work(", 1
)[0]
metered_sum_upper = goal_shortcuts.split("def proof_unsigned_sum_upper_shape_with_work(", 1)[1].split(
    "def proof_unsigned_legacy_goal_shapes_with_work(", 1
)[0]
metered_unit_increment = goal_shortcuts.split("def proof_unsigned_unit_increment_order_shape_with_work(", 1)[1].split(
    "def proof_unsigned_legacy_goal_shapes_with_work(", 1
)[0]
metered_strict_progress = strict_progress_work.split("def proof_unsigned_strict_progress_shape_with_work(", 1)[1]
metered_sum_progress = strict_progress_work.split("def proof_unsigned_nonwrapping_sum_progress_with_work(", 1)[1].split(
    "def proof_unsigned_strict_progress_shape_with_work(", 1
)[0]
for charged_helper in (
    "proof_linear_strip_parens_with_work",
    "proof_unsigned_width_in_expression_with_work",
    "proof_sum_upper_witness_with_work",
    "proof_unsigned_witness_terms_equal_with_work",
    "proof_unsigned_peer_nameable_with_work",
    "proof_unsigned_peer_width_matches_with_work",
):
    assert charged_helper in metered_sum_upper, charged_helper
for charged_helper in (
    "proof_unsigned_unit_increment_base_with_work",
    "proof_unsigned_witness_terms_equal_with_work",
    "proof_unsigned_width_in_expression_with_work",
    "proof_unsigned_expression_safe_with_facts_work",
):
    assert charged_helper in metered_unit_increment, charged_helper
for charged_helper in (
    "proof_unsigned_nonwrapping_sum_progress_with_work",
):
    assert charged_helper in metered_strict_progress, charged_helper
assert "proof_unsigned_sum_range_safe_with_work" in metered_sum_progress
assert "proof_unsigned_progress_positive_with_work" in metered_sum_progress
for raw_reader in (
    "proof_unsigned_progress_positive(",
    "proof_sum_upper_witness(",
    "proof_sum_range_safe(",
    "proof_unsigned_width_in_expression(",
    "proof_peer_unsigned_width(",
    "proof_expr_equal(",
):
    assert raw_reader not in strict_progress_work, raw_reader
assert "proof_unsigned_strict_progress_shape_with_work(goal, facts, markers.witnesses, marker_scale.scale, budget, exhausted)" in legacy_shape_adapter
assert "proof_unsigned_strict_progress_shape(facts, goal)" not in legacy_shape_adapter
assert "proof_unsigned_literal_progress(facts, goal, annotations)" not in legacy_shape_adapter
assert "proof_unsigned_maximum_equality(facts, goal, annotations)" not in legacy_shape_adapter
numeric_literal_sort = (ROOT / "src/proof/replay/numeric_literal_sort.elisa").read_text(encoding="utf-8")
literal_sort_reader = numeric_literal_sort.split("def proof_replay_numeric_literal_sort(", 1)[1].split("\n        def ", 1)[0]
assert "return (false, 0, false, 0)" in literal_sort_reader
assert "proof_unsigned_sum_upper_shape_with_work(goal, facts, markers.witnesses, budget, exhausted)" in legacy_shape_adapter
assert "proof_unsigned_unit_increment_order_shape_with_work(goal, facts, markers.witnesses, budget, exhausted)" in legacy_shape_adapter
assert "proof_scalar_witness_markers_with_work(facts, true, budget, exhausted)" in legacy_shape_adapter
assert "reservation" not in legacy_shape_adapter
goal_depth = (ROOT / "src/proof/linear/congruence_goal_depth.elisa").read_text(encoding="utf-8")
assert "proof_unsigned_legacy_goal_shapes_with_work(goal, facts, annotations, budget, exhausted)" in goal_depth
assert "proof_closed_signed_literal_comparison_with_work(stripped_goal.expression, budget, exhausted)" in goal_depth
assert "proof_closed_signed_literal_comparison(goal)" not in goal_depth
assert "proof_closed_literal_comparison_with_work(stripped_goal.expression, budget, exhausted)" in goal_depth
assert "proof_closed_literal_comparison(goal)" not in goal_depth
fixed_width_helpers = (ROOT / "src/proof/linear/fixed_width_arithmetic_integrated_helpers.elisa").read_text(encoding="utf-8")
signed_literal_reader = fixed_width_helpers.split("def proof_signed_literal_comparison_constant_with_work(", 1)[1].split(
    "def proof_closed_signed_literal_comparison_with_work(", 1
)[0]
assert "proof_linear_safety_work_charge(budget, exhausted, 1)" in signed_literal_reader
assert "proof_nonnegative_literal_constant_with_work" in signed_literal_reader
signed_literal_comparison = fixed_width_helpers.split("def proof_closed_signed_literal_comparison_with_work(", 1)[1].split(
    "def proof_closed_literal_comparison_with_work(", 1
)[0]
assert "proof_linear_strip_parens_with_work" in signed_literal_comparison
assert "proof_signed_literal_comparison_constant_with_work" in signed_literal_comparison
closed_literal = fixed_width_helpers.split("def proof_closed_literal_comparison_with_work(", 1)[1].split(
    "def proof_closed_integer_arithmetic(", 1
)[0]
assert "proof_linear_strip_parens_with_work" in closed_literal
assert "proof_linear_safety_work_charge(budget, exhausted, sview_len(left_value))" in closed_literal
assert "proof_linear_safety_work_charge(budget, exhausted, sview_len(right_text))" in closed_literal
for raw_call in (
    "proof_unsigned_sum_upper_shape(facts, goal)",
    "proof_unsigned_strict_progress_shape(facts, goal)",
    "proof_unsigned_literal_progress(facts, goal, annotations)",
    "proof_unsigned_maximum_equality(facts, goal, annotations)",
):
    assert raw_call not in goal_depth
bounded_receiver = (ROOT / "src/proof/linear/unsigned_widening.elisa").read_text(encoding="utf-8")
safe_receiver = bounded_receiver.split("def proof_bounded_u8_receiver_with_work(", 1)[1]
for metered_helper in (
    "proof_scalar_witness_markers_with_work",
    "proof_linear_safety_marker_scale_with_work",
    "proof_signed_width_in_expression_with_scale_work",
    "proof_linear_safety_scalar_witness_with_work",
    "proof_collect_fact_bounds_with_work",
    "proof_close_equalities_with_work",
    "proof_signed_safety_bounds_from_base_with_work",
    "proof_signed_expression_safe_with_bounds_work",
    "proof_interval_with_work",
):
    assert metered_helper in safe_receiver, metered_helper
for unmetered_helper in (
    "proof_scalar_term_witnessed(",
    "proof_signed_width_in_expression(",
    "proof_signed_expression_safe(",
    "proof_collect_bounds(",
    "proof_interval(",
):
    assert unmetered_helper not in safe_receiver, unmetered_helper

# Result postconditions may flow through one source-local integer only when its checked sort and
# type identity match the function return type and the final return names that unique local.
# Extra locals, shadowing, and changed returns stay unsupported.
postcondition_returns = postcondition_inventory.split(
    "def proof_source_postcondition_ast_inventory_collect(", 1
)[1].split("def proof_source_signature_postcondition_ast_inventory_collect(", 1)[0]
for requirement in (
    "local_return_count: mutable usize = 0",
    "local_return_count <- local_return_count + 1",
    'local_name == "result" or local_name == "old"',
    "initializer == Ast::Expr.Absent or initializer == Ast::Expr.Invalid",
    'proof_report_source_postcondition_work_charge(sview_len("result"), source_work)',
    'proof_report_source_postcondition_work_charge(sview_len("old"), source_work)',
    'proof_report_source_postcondition_work_charge(sview_len(return_type_name), source_work)',
    "local_sort.type_name != return_type_name",
    "parameter.name == local_name",
    "Ast::Stmt.VarDecl(local_name, Ast::Expr.Ident(local_type, local_type_position), initializer, local_position)",
    'local_sort.sort != "integer" or return_type_sort != "integer"',
    "local_sort.type_identity != return_type_identity",
    "initializer_scan: (complete: bool, has_result: bool, has_old: bool, has_match: bool)",
    "initializer_scan.has_result or initializer_scan.has_old",
    "initializer_position: Ast::Pos = Ast::expr_pos(initializer)",
    "initializer_position.offset <= local_position.offset",
    "initializer_position.end_offset <= initializer_position.offset",
    "local_return_end_offset <- initializer_position.end_offset",
    "Ast::Expr.Ident(returned_name, return_position)",
    "returned_name != local_return_name",
    "return_position.offset <= local_return_end_offset",
):
    assert requirement in postcondition_returns, requirement
assert "local_return_count != 1" in postcondition_returns
assert "return_supported <- false" in postcondition_returns.split("_:", 1)[1]
local_return_fixture = (ROOT / "scripts/test_direct_api_semantic_admission.py").read_text(encoding="utf-8")
assert 'ensure result == 7\\n    status: u8 = 7\\n    return status' in local_return_fixture
shared_goal = linear_goal_api.split("def proof_goal_with_shared_work(", 1)[1].split("def proof_goal_with_precomputed_operator_mask(", 1)[0]
shared_float = shared_goal.split("if (proof_float_mode can Global.Read):", 1)[1].split("goal_width_probe:", 1)[0]
assert "proof_goal_tactic_preflight_charge_scaled(preflight_work, float_square_cost, 8)" in shared_float
assert "proof_goal_tactic_preflight_charge_scaled(preflight_work, shape_cost, 16)" in shared_float
assert "proof_float_goal_with_work(facts, goal, operator_mask, &float_work, &float_exhausted)" in shared_float
assert "proof_float_goal(facts, goal)" not in shared_float
assert "proof_float_propositional_goal_with_shared_work(facts, goal, operator_mask, preflight_work, PROOF_LINEAR_TACTIC_PREFLIGHT_WORK_LIMIT)" in shared_float
goal_replay = kernel_resource_model.split("def proof_kernel_replay_goal_depth_remaining_with_work(", 1)[1]
goal_root_gate = goal_replay.index("if not (proof_kernel_replay_unsigned_safe_closing_with_goal_work(nodes, children, goal_root")
binary_solver = goal_replay.index("proof_kernel_replay_goal_binary_with_work(nodes, children, facts")
assert goal_root_gate < binary_solver and "proof_kernel_replay_signed_expression_safe_with_bounds_goal_work(nodes, children, goal_root" in goal_replay[goal_root_gate:binary_solver]
unsafe_goal_fallback = goal_replay[goal_root_gate:].split("linear_certificate_closed:", 1)[0]
assert "return (proof_kernel_replay_nested_conditional_goal(" in unsafe_goal_fallback
assert "proof_kernel_replay_goal_binary_with_work(" not in unsafe_goal_fallback
print("source admission budget: bounded fallback, float containment, and normalized-goal gates")
