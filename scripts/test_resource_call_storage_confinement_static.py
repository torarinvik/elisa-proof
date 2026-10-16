"""Guard the source-recomputed storage premises for resource-call lending."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following.strip())
            return "\n".join(body)
    raise AssertionError(f"function {name} not found in {path}")


resource_source_path = ROOT / "src/proof/replay/resource_call_source_validation.elisa"
resource_lend_return_guard = function_body(resource_source_path, "proof_replay_resource_lend_return_is_confined")
assert "proof_type_is_reference_free_with_work(declared_return_type" in resource_lend_return_guard
assert "return false if not return_reference_free" in resource_lend_return_guard
assert "proof_type_contains_borrowed_view_with_work(declared_return_type" in resource_lend_return_guard

resource_lend_storage_guard = function_body(resource_source_path, "proof_replay_resource_lend_storage_is_confined_with_work")
assert "proof_replay_thread_type_mentions_owner_generic_with_work" in resource_lend_storage_guard
assert "proof_type_is_reference_free_with_work(target_type.target" in resource_lend_storage_guard
assert "proof_replay_thread_type_contains_borrowed_storage(target_type.target" in resource_lend_storage_guard
assert "not borrowed.complete or borrowed.borrowed" in resource_lend_storage_guard

resource_call_argument_guard = function_body(resource_source_path, "proof_replay_resource_call_arguments_match_with_work")
assert "proof_replay_resource_lend_storage_is_confined_with_work(report, parameters, parameter_markers_by_index" in resource_call_argument_guard

resource_purity_path = ROOT / "src/proof/replay/resource_call_pure_source.elisa"
resource_conversion_source = (ROOT / "src/proof/resources/places_and_calls.elisa").read_text(encoding="utf-8")
pure_conversion = function_body(ROOT / "src/proof/resources/places_and_calls.elisa", "proof_resource_pure_conversion")
conversion_names = re.findall(r'"([A-Za-z0-9_]+)"', pure_conversion)
conversion_count = re.search(r"PROOF_RESOURCE_PURE_CONVERSION_METHOD_COUNT: usize = (\d+)", resource_conversion_source)
assert conversion_count is not None and int(conversion_count.group(1)) == len(conversion_names)
assert len(conversion_names) == len(set(conversion_names))
resource_expression_checker = function_body(ROOT / "src/proof/resources/expression_checker.elisa", "proof_resource_check_expression")
assert "proof_runtime_builtin_numeric_cast(callee, arguments.count, functions)" in resource_expression_checker
assert "functions.externs.custom_cast_hook_present" in resource_expression_checker
assert resource_expression_checker.index("proof_runtime_builtin_numeric_cast(callee, arguments.count, functions)") < resource_expression_checker.index("proof_source_effect_field_conversion_lookup(report, method_call.method)")
assert "numeric_cast.known or source_conversion_unshadowed" in resource_expression_checker
resource_scalar_guard = function_body(resource_purity_path, "proof_replay_resource_call_scalar_type_with_work")
assert "proof_replay_resource_scalar_type_with_work(expression, report, source_work, 0)" in resource_scalar_guard
assert "not scalar.complete or not scalar.scalar" in resource_scalar_guard
assert "proof_replay_control_match_guard_scalar_type(expression)" in resource_scalar_guard
resource_purity_function = function_body(resource_purity_path, "proof_replay_resource_call_pure_function")
assert "proof_structural_typed_operator_statements_have_overload(body, parameters, declaration_line, operator_source, 0, entry.owner, true)" in resource_purity_function
assert "or overloaded_operator" in resource_purity_function
resource_pure_expr = function_body(resource_purity_path, "proof_replay_resource_call_pure_expr")
assert "proof_replay_call_field_conversion_selector_with_work(method, source_work)" in resource_pure_expr
assert "not selector.complete or not selector.numeric_selector" in resource_pure_expr
assert "call_target.conversions.field_dispatch_imports_present" in resource_pure_expr
assert "proof_replay_call_field_dispatch_is_accounted_for(callee_expression, arguments, labels, bindings, call_target, source_work)" in resource_pure_expr
assert "return false if arguments.count != 0 or labels.count != 0" in resource_pure_expr
assert "return proof_replay_resource_call_pure_expr(report, operator_source, index, aliases, owner_entry, owner_line, owner_offset, receiver, parameters, source_work, depth + 1)" in resource_pure_expr
call_field_dispatch = function_body(ROOT / "src/proof/replay/source_call_bindings.elisa", "proof_replay_call_field_dispatch_is_accounted_for")
assert "not selector.pure_conversion and not selector.numeric_selector" in call_field_dispatch
assert "proof_replay_call_field_conversion_selector_with_work(method, work)" in call_field_dispatch
assert "if not selector.numeric_selector" in call_field_dispatch
numeric_selector = function_body(ROOT / "src/proof/check/fact_call_shapes.elisa", "proof_fact_numeric_cast_target_index")
assert '"int" ->' in numeric_selector and '"uintptr" ->' in numeric_selector
assert "return proof_builtin_scalar_type_name(receiver_type_name)" in call_field_dispatch
assert "call_target.conversions.field_conversion_custom_cast_present" in call_field_dispatch
field_method_charge = function_body(ROOT / "src/proof/replay/source_call_bindings.elisa", "proof_replay_call_field_method_check_charge")
assert "proof_replay_call_work_add(work, 1)" in field_method_charge
assert "proof_replay_call_work_add(work, sview_len(method))" in field_method_charge
assert call_field_dispatch.count("proof_replay_call_field_method_check_charge(method, work)") == 2
collection_builtin = function_body(ROOT / "src/proof/replay/source_call_bindings.elisa", "proof_replay_call_field_collection_builtin_is_modeled")
assert collection_builtin.count("proof_replay_call_field_method_check_charge(method, work)") == 2
assert "method_declared.present" in call_field_dispatch
assert "call_target.conversions.field_conversion_custom_cast_present" in call_field_dispatch
resource_name_counts = function_body(ROOT / "src/proof/replay/resource_call_name_counts.elisa", "proof_replay_resource_call_name_counts_match")
assert "proof_replay_resource_call_name_is_irrelevant_with_work(report, operator_source" in resource_name_counts
assert "index.source_counts[row] > index.event_counts[row]" in resource_name_counts
assert "and not proof_replay_resource_call_name_is_irrelevant_with_work" in resource_name_counts
assert "omission_sources_clear" in resource_name_counts
opaque_targets = function_body(
    ROOT / "src/proof/replay/resource_call_source_validation.elisa",
    "proof_replay_resource_call_has_opaque_target_with_work",
)
assert "Ast::Decl.Import(_, _) | Ast::Decl.Invalid" in opaque_targets
assert "proof_replay_summary_has_unresolved_import" in resource_name_counts
omission_classifier = function_body(
    ROOT / "src/proof/replay/resource_call_shadow_validation.elisa",
    "proof_replay_resource_call_name_is_irrelevant_with_work",
)
for omission_gate in (
    "not omission_sources_clear",
    "proof_replay_resource_call_group_has_nonfunction(index, wanted, source_work)",
    "proof_replay_resource_call_shadow_name_in_statements(owner_body, wanted, source_work, 0)",
    "entry.name != wanted or not entry.is_function or entry.is_lemma",
    "not proof_replay_resource_call_pure_function(report, operator_source, index, aliases, entry, source_work, 0)",
):
    assert omission_gate in omission_classifier, omission_gate
assert "not scalar_parameter.complete or not scalar_parameter.scalar" in omission_classifier
assert "markers.reference or markers.mutable_reference or markers.is_mutable" in omission_classifier
assert "syntax.has_reference" in omission_classifier
assert "sview_parameter.sview_type" in omission_classifier
assert "if return_type is declared_return_type:" in omission_classifier
assert re.search(r"else:\s+return false", omission_classifier)
assert "not scalar_return.complete or not scalar_return.scalar" in omission_classifier
assert "return_markers.reference or return_markers.mutable_reference or return_markers.is_mutable" in omission_classifier
assert "return_syntax.has_reference" in omission_classifier
assert "sview_return.sview_type" in omission_classifier

# Collection `.count` is a scalar-copy exception only when the declared type was
# classified completely. An unresolved alias that happens to be named `darray`
# must not suppress region/resource tracking.
resource_statement = function_body(
    ROOT / "src/proof/resources/statement_checker.elisa",
    "proof_resource_check_statements",
)
assert "if local_markers.complete and proof_resource_type_is_collection(type_expression):" in resource_statement
extent_classifier = function_body(
    ROOT / "src/proof/resources/place_paths.elisa",
    "proof_resource_binding_is_extent_bearing",
)
assert "slot >= state.bindings.binding_type_marker_complete.count or not state.bindings.binding_type_marker_complete[slot]" in extent_classifier
marker_summary = function_body(
    ROOT / "src/proof/resources/type_markers.elisa",
    "proof_resource_type_marker_summary_with_owner_work_depth",
)
assert "lookup.declarations > 0 and proof_resource_marker_builtin_collection_type_name(name)" in marker_summary

# Nested control-flow GetElse forms stay outside the admitted proof language. The
# parser retains their recovery blocks, but the checker only handles recoveries at
# statement-value roots; otherwise a recovery can carry a hidden memory access that
# the statement-level index walk intentionally does not visit.
runtime_support = function_body(
    ROOT / "src/proof/check/runtime_support_and_calls.elisa",
    "proof_statement_value_supported",
)
assert all(text in runtime_support for text in (
    "Ast::Expr.GetElse(guarded, recovery, _):",
    "return false if recovery.count == 0",
    "return proof_expr_supported(guarded) and proof_runtime_expression_calls_allowed(guarded, functions)",
))
expression_support = function_body(
    ROOT / "src/proof/expr/pattern_support.elisa",
    "proof_expr_supported_depth_with_work",
)
assert re.search(r"Ast::Expr.GetElse\(_, _, _\):\s+return false", expression_support)
recovery_extractor = function_body(
    ROOT / "src/proof/check/index_checks.elisa",
    "proof_statement_getelse_recovery",
)
assert all(text in recovery_extractor for text in (
    "Ast::Stmt.Return(value, _):",
    "Ast::Stmt.Expr(expression, _):",
    "Ast::Stmt.VarDecl(_, _, initializer, _):",
    "Ast::Stmt.Assign(_, _, initializer, _):",
    "return (true, guarded, recovery, position.line)",
))
assert "Ast::Stmt.If(" not in recovery_extractor
index_safety_getelse = function_body(
    ROOT / "src/proof/check/index_safety_value.elisa",
    "proof_check_index_safety_value",
)
assert "Ast::Expr.GetElse(guarded, _, getelse_position):" in index_safety_getelse

# A shared extent is trusted only after every formal has been classified. An
# incomplete frame must revoke both the count-only and all-fields stability facts.
shared_borrows = function_body(
    ROOT / "src/proof/check/shared_borrows.elisa",
    "proof_record_shared_borrows",
)
assert (
    "if not closed_frame:\n"
    "report.aliases.shared_extent_names.clear()\n"
    "report.aliases.shared_fixed_names.clear()"
) in shared_borrows

resource_coverage = function_body(ROOT / "src/proof/replay/resource_call_site_validation.elisa", "proof_replay_resource_call_coverage_for_owner_with_work")
assert "proof_replay_resource_call_name_counts_match(cache.resource_call_owner_snapshots[located.row].source_calls, event_names, report, cache.scratch, cache.deterministic_calls.declaration_index, cache.deterministic_calls.alias_index, parameters, body, source_work)" in resource_coverage
assert "proof_replay_source_call_target_context(parameters, cache.scratch.source.source_annotations, &cache.scratch, entry.name, entry.owner, owner_line, owner_offset, source_work, true, true)" in resource_coverage
assert "proof_replay_source_calls_with_target_work(parameters, body, cache.scratch.source.source_annotations, &source_calls, call_target, source_work)" in resource_coverage
assert "call_target.selection.unresolved_dispatch_found" in resource_coverage
resource_site_match = function_body(ROOT / "src/proof/replay/resource_call_site_validation.elisa", "proof_replay_resource_call_site_matches_owner_with_work")
assert "source_call_expression_at_owner_with_work" in resource_site_match
assert "not selected.known and not scoped.known" in resource_site_match
assert "proof_replay_resource_scoped_callee_row_with_work(report, owner_module, scoped.callee" in resource_site_match
assert "callee_owner.matches != 1" in resource_site_match
resource_event_walk = function_body(ROOT / "src/proof/replay/certificate_validation.elisa", "proof_replay_resource_event_facts_with_owner")
assert "proof_replay_resource_call_coverage_for_owner_with_work(report, root, active_owner" in resource_event_walk
assert "proof_replay_resource_event_facts_with_owner(report, node.left, node.left, 0, callee_root.name" in resource_event_walk
resource_fact_candidate = function_body(
    ROOT / "src/proof/replay/kernel_fact_root_index.elisa",
    "proof_replay_kernel_fact_root_candidate_matches_with_stack",
)
assert all(text in resource_fact_candidate for text in (
    'if require_unconditional_source and trace.kind not in {"global-constant", "global-constant-qualified", "global-mutable-array-type", "global-mutable-array-index-bound", "const-enum-member-value", "precondition"}',
    "not proof_replay_trace_lookup_charge(report)",
    "proof_replay_kernel_trace_valid_memo(report, trace_index, owner",
    'if require_unconditional_source and trace.kind == "precondition":',
    "proof_replay_kernel_fact_trace_is_valid_with_stack(report, trace, trace_index, owner",
    "structural_cache, true)",
))
resource_fact_trace = function_body(
    ROOT / "src/proof/replay/certificate_validation.elisa",
    "proof_replay_kernel_fact_root_is_traced_with_stack",
)
assert "trace_index <- proof_replay_trace_chain_next(report, trace_index)" in resource_fact_trace
resource_fact_validation = function_body(
    ROOT / "src/proof/replay/certificate_validation.elisa",
    "proof_replay_kernel_fact_trace_is_valid_with_stack",
)
assert 'if allow_stable_resource_precondition and trace.kind == "precondition":' in resource_fact_validation
assert "proof_replay_resource_disjoint_precondition_is_stable_cached" in resource_fact_validation
resource_disjoint_precondition = function_body(
    ROOT / "src/proof/replay/precondition_validation.elisa",
    "proof_replay_resource_disjoint_precondition_is_stable",
)
assert 'Ast::Expr.Binary(Ast::Expr.Ident(left_name, _), TokenKind.BangEq, Ast::Expr.Ident(right_name, _), _)' in resource_disjoint_precondition
assert "proof_replay_resource_disjoint_precondition_body_site_matches" in resource_disjoint_precondition
assert "parameter.is_mutable or parameter.has_default or parameter.is_affine" in resource_disjoint_precondition
assert 'Ast::Expr.Ident("usize", _)' in resource_disjoint_precondition
assert "left_matches != 1 or right_matches != 1" in resource_disjoint_precondition
assert "proof_replay_source_body_touches_with_work(report.source.source_declarations, body, left_name, true" in resource_disjoint_precondition
assert "proof_replay_source_body_touches_with_work(report.source.source_declarations, body, right_name, true" in resource_disjoint_precondition
assert "proof_source_expression_has_overloaded_operator_with_work(trace.expression" in resource_disjoint_precondition
checked_access_alias_names = function_body(
    ROOT / "src/proof/model/report_checked_access_alias_names.elisa",
    "proof_checked_access_alias_mentions_name_with_work",
)
assert "proof_replay_summary_expr_cost_with_limit(expression, &cost, work, PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT)" in checked_access_alias_names
assert "target_length: usize = sview_len(target)" in checked_access_alias_names
assert "multiplier: usize = target_length + 1" in checked_access_alias_names
assert "cost > remaining / multiplier" in checked_access_alias_names
assert "work <- work + cost * multiplier" in checked_access_alias_names
checked_access_alias_store = function_body(
    ROOT / "src/proof/model/report_checked_access_inventory.elisa",
    "proof_checked_access_alias_store",
)
assert "proof_checked_access_alias_mentions_name_with_work(stored, name, work)" in checked_access_alias_store
assert "proof_checked_access_alias_mentions_name_with_work(prior_value, name, work)" in checked_access_alias_store
assert "proof_expr_mentions_name(stored, name)" not in checked_access_alias_store
assert "proof_expr_mentions_name(prior_value, name)" not in checked_access_alias_store
mutable_array_source = ROOT / "src/proof/replay/global_mutable_array_validation.elisa"
bound_precondition = function_body(mutable_array_source, "proof_replay_global_mutable_array_bound_precondition")
assert "Ast::Expr.Ident(\"usize\", _)" in bound_precondition
assert "if parameter.name == bound_parameter" in bound_precondition
assert "not unsigned_parameter" in bound_precondition
assert "proof_replay_source_body_declares_with_work(report.source.source_declarations, owner_body, bound_parameter, source_work)" in bound_precondition
assert "proof_replay_source_body_touches_with_work(report.source.source_declarations, owner_body, bound_parameter, true, source_work)" in bound_precondition
assert "required_parameter == bound_parameter and required_extent == extent" in bound_precondition
assert "proof_source_analysis_operator_mask_from_source(report.source.source_declarations, report.source.source_annotations, source_work)" in bound_precondition
assert "proof_source_expression_has_overloaded_operator_with_work(expression, operator_mask_status.mask, source_work, operator_work_exhausted)" in bound_precondition
assert "not operator_mask_status.complete" in bound_precondition
assert "or operator_work_exhausted" in bound_precondition
mutable_array_validate = function_body(mutable_array_source, "proof_replay_global_mutable_array_type_fact_is_valid_after_preflight")
assert "proof_replay_global_mutable_array_bound_precondition(report, owner_parameters, owner_body, trace.expression, extent, trace.line, source_work)" in mutable_array_validate
assert "global_matches != 1 or not global_valid or extent < 0" in mutable_array_validate
assert "not proof_replay_global_mutable_array_fact_shape(trace.expression, global_name, extent, global_position)" in mutable_array_validate
assert "not source_search_complete or root_binding_count != 1" in mutable_array_validate
mutable_array_fact_gate = function_body(mutable_array_source, "proof_replay_global_mutable_array_type_fact_is_valid_with_work")
assert "proof_source_analysis_operator_mask_from_source(report.source.source_declarations, report.source.source_annotations, source_work)" in mutable_array_fact_gate
assert 'Ast::Expr.Binary(Ast::Expr.Ident(_, _), TokenKind.Lt, Ast::Expr.Field(Ast::Expr.Ident(_, _), "count", _), _):' in mutable_array_fact_gate
assert "proof_source_expression_has_overloaded_operator_with_work(trace.expression, operator_mask_status.mask, source_work, operator_work_exhausted)" in mutable_array_fact_gate
root_array = function_body(mutable_array_source, "proof_replay_global_mutable_array_find_root_with_work")
assert "annotation_matches == 1" in root_array and "proof_replay_global_mutable_array_annotation_count_with_work" in root_array
fixed_extent = function_body(mutable_array_source, "proof_replay_global_mutable_array_literal_extent")
assert "Ast::Expr.Index(Ast::Expr.Ident(element, _), Ast::Expr.IntLit(extent, _), _)" in fixed_extent
assert "Ast::Expr.IndexN(Ast::Expr.Ident(\"array\", _), arguments, _)" in fixed_extent
assert "return extent if extent >= 0" in fixed_extent
precondition_source = ROOT / "src/proof/replay/precondition_validation.elisa"
precondition_liveness = function_body(precondition_source, "proof_replay_precondition_live_at_consumer")
assert "proof_replay_expression_contains_call_node(trace.expression, 0)" in precondition_liveness
assert "depends_on_mutable_state <- true if call_dependent" in precondition_liveness
assert "statement, call_dependent, source_work, 0" in precondition_liveness
global_liveness = function_body(
    ROOT / "src/proof/replay/precondition_mutable_global_validation.elisa",
    "proof_replay_precondition_statement_touches_mutable_global",
)
assert "all_roots or proof_expr_mentions_name(expression, name)" in global_liveness
precondition_harness = (ROOT / "scripts/tests/test_replay_scope_and_context_holes.py").read_text(encoding="utf-8")
assert '"global mutable precondition_state: i64 = 0\\n"' in precondition_harness
assert "precondition_state <- 1" in precondition_harness
assert "precondition_state_is_zero" in precondition_harness
assert "A call in a requires clause can hide a read of mutable global state." in precondition_harness
assert "proof_replay_fact_trace_entry(&report, qualified_precondition_index) can Global{Read,Write}), 128" in precondition_harness
const_enum_value = function_body(ROOT / "src/proof/replay/variant_exclusion_validation.elisa", "proof_replay_const_enum_member_value_valid")
assert "left.const_enums != 1" in const_enum_value and "right.const_enums != 1" in const_enum_value
assert "proof_replay_const_enum_member_value_valid(report, trace, source_work)" in function_body(ROOT / "src/proof/replay/boundary_trace_shapes.elisa", "proof_replay_boundary_trace_shape_valid_with_cache")
assert "proof_replay_kernel_fact_root_is_traced_with_stack(report, fact, active_owner, dependency_stack, false, true" in resource_event_walk

resource_snapshot_path = ROOT / "src/proof/replay/resource_call_site_snapshot.elisa"
resource_snapshot_select = function_body(resource_snapshot_path, "proof_replay_resource_call_owner_snapshot_select")
assert "cached.count != 1" in resource_snapshot_select
assert "resolve_callee_owner_at_offset_with_work" in resource_snapshot_select
resource_snapshot_lookup = function_body(resource_snapshot_path, "proof_replay_resource_call_owner_snapshot_lookup")
assert "snapshot.call_offsets[row] == offset" in resource_snapshot_lookup
assert "snapshot.call_counts[row] == 0" in resource_snapshot_lookup
resource_snapshot_build = function_body(resource_snapshot_path, "proof_replay_resource_call_owner_snapshot_build")
assert "snapshot.call_counts[existing] <- snapshot.call_counts[existing] + 1" in resource_snapshot_build

resource_name_counts_path = ROOT / "src/proof/replay/resource_call_name_counts.elisa"
event_offset_guard = function_body(resource_name_counts_path, "proof_replay_resource_call_event_offsets_unique_with_work")
assert "return false if values[slot] == offset" in event_offset_guard
assert "proof_replay_resource_call_event_offsets_unique_with_work(event_offsets, source_work)" in resource_coverage

source_call_api = function_body(ROOT / "src/proof/replay/source_call_api.elisa", "proof_replay_source_calls_with_target_work")
assert "capture_resource_call_expressions <- false" in source_call_api
assert "body_expression_capture: bool = call_target.capture.capture_resource_call_expressions" in source_call_api
assert "capture_resource_call_expressions <- body_expression_capture" in source_call_api

source_call_target = function_body(ROOT / "src/proof/replay/source_call_target_context.elisa", "proof_replay_source_call_target_context")
assert "include_nonassert_contract_calls: true" in source_call_target
assert "track_unresolved_dispatch: true" in source_call_target
assert "field_conversion_parameters: parameters" in source_call_target
assert "field_conversion_declared_types: scratch.source_types.source_effect_index.types.declared_types" in source_call_target
collection_shadow_scan = function_body(ROOT / "src/proof/replay/source_call_target_context.elisa", "proof_replay_collection_name_shadowed")
assert "collection_method_name_shadow_checked" in collection_shadow_scan
assert "proof_replay_collection_name_shadowed_in" in collection_shadow_scan
source_index_reset = function_body(ROOT / "src/proof/check/source_effect_index_reset.elisa", "proof_source_analysis_indexes_reset")
assert "report.source.collection_method_name_shadowed <- false" in source_index_reset
assert "report.source.collection_method_name_shadow_checked <- false" in source_index_reset

source_call_api_path = ROOT / "src/proof/replay/source_call_api.elisa"
source_call_api_text = source_call_api_path.read_text(encoding="utf-8")
source_call_api = function_body(source_call_api_path, "proof_replay_source_calls_with_work")
assert "require_resolved_dispatch: bool = false" in source_call_api_text
assert "target.selection.track_unresolved_dispatch <- select_target or require_resolved_dispatch" in source_call_api
assert "require_resolved_dispatch and target.selection.unresolved_dispatch_found" in source_call_api
source_call_expression = function_body(ROOT / "src/proof/replay/source_call_coverage.elisa", "proof_replay_call_expression_with_index")
assert "Ast::Expr.Field(_, method, _)" in source_call_expression
assert "proof_replay_call_field_dispatch_is_accounted_for" in source_call_expression
assert "call_target.selection.unresolved_dispatch_found <- true" in source_call_expression
field_collection_builtin = function_body(ROOT / "src/proof/replay/source_call_bindings.elisa", "proof_replay_call_field_collection_builtin_is_modeled")
assert "proof_replay_call_receiver_type" in field_collection_builtin
assert "proof_replay_call_type_head_name" in field_collection_builtin
assert 'receiver_type_name == "darray"' in field_collection_builtin
assert "proof_replay_call_conversion_builtin_generic_type_head" in field_collection_builtin
assert 'method not in {"push", "extend", "clear", "resize", "pop", "truncate"}' in field_collection_builtin
assert "call_target.conversions.field_dispatch_imports_present or call_target.conversions.collection_method_name_shadowed" in field_collection_builtin
assert "proof_replay_call_receiver_has_place_root(receiver, work, 0)" in field_collection_builtin
assert "argument_names.count != 0 and argument_names.count != arguments.count" in field_collection_builtin
assert 'if method == "clear":' in field_collection_builtin
assert 'return false if arguments.count != 0' in field_collection_builtin
assert 'elif method == "pop":' in field_collection_builtin
assert 'return false if arguments.count > 1' in field_collection_builtin
assert 'return false if arguments.count != 1' in field_collection_builtin
assert 'label != ""' in field_collection_builtin
assert "proof_replay_call_argument_is_move(argument, work, 0)" in field_collection_builtin
assert "proof_replay_call_field_conversion_name_present(method, call_target, work)" in field_collection_builtin
assert "declared.complete and not declared.present" in field_collection_builtin
receiver_type_resolution = function_body(ROOT / "src/proof/replay/source_call_bindings.elisa", "proof_replay_call_receiver_type")
source_call_statements = function_body(ROOT / "src/proof/replay/source_call_coverage.elisa", "proof_replay_call_statements")
assert "active_matches != 1" in receiver_type_resolution
assert "field_conversion_parameters" in receiver_type_resolution
assert "captured_local_type_names.count != call_target.capture.captured_local_type_expressions.count" in receiver_type_resolution
assert "local_matches == 1" in receiver_type_resolution
assert "selected <- call_target.capture.captured_local_type_expressions[local_index]" in receiver_type_resolution
assert "call_target.capture.captured_local_type_names.push(name)" in source_call_statements
assert "call_target.capture.captured_local_type_expressions.push(type_expression)" in source_call_statements
producer_collection_builtin = function_body(
    ROOT / "src/proof/resources/collection_builtin_admission.elisa", "proof_resource_collection_builtin_with_state"
)
producer_darray_type = function_body(
    ROOT / "src/proof/resources/collection_builtin_admission.elisa", "proof_resource_type_name_is_unshadowed_darray"
)
assert "proof_function_index_of_current(functions, state.context.function_name)" in producer_darray_type
assert "proof_source_conversion_alias_target_in_owner(\"darray\", owner, report)" in producer_darray_type
assert 'proof_source_conversion_alias_target_in_owner("darray", "", report)' in producer_darray_type
assert 'proof_source_conversion_alias_target("darray", report)' in producer_darray_type
assert "owner_target.count != 0 or owner_target.nominal or owner_target.blocks_parent" in producer_darray_type
assert "root_target.count != 0 or root_target.nominal or root_target.blocks_parent" in producer_darray_type
assert 'global_target.complete and global_target.count == 0' in producer_darray_type
producer_darray_classifier = function_body(
    ROOT / "src/proof/resources/collection_builtin_admission.elisa", "proof_resource_type_is_darray"
)
assert producer_darray_classifier.count("proof_resource_type_name_is_unshadowed_darray(report, state, functions)") == 2
assert 'report.source_types.source_effect_index.conversions.field_dispatch_imports_present' in producer_collection_builtin
assert 'report.source_types.source_effect_index.conversions.collection_method_name_shadowed' in producer_collection_builtin
resource_includes = (ROOT / "src/proof/resources.elisa").read_text(encoding="utf-8")
assert resource_includes.index('include "./resources/places_and_calls.elisa"') < resource_includes.index('include "./resources/collection_builtin_admission.elisa"') < resource_includes.index('include "./resources/expression_checker.elisa"')
resource_expression_calls = function_body(
    ROOT / "src/proof/resources/expression_checker.elisa", "proof_resource_check_expression"
)
assert "proof_resource_collection_builtin_with_state(callee, functions, report, state)" in resource_expression_calls
producer_methods = set(re.findall(r'method != "([a-z_]+)"', producer_collection_builtin))
replay_methods_match = re.search(
    r'method not in \{([^}]*)\}', field_collection_builtin
)
assert replay_methods_match, "resource-call replay collection method set is missing"
replay_methods = set(re.findall(r'"([a-z_]+)"', replay_methods_match.group(1)))
assert producer_methods == replay_methods, (producer_methods, replay_methods)
resource_write_coverage = function_body(
    ROOT / "src/proof/replay/resource_write_coverage.elisa",
    "proof_replay_resource_write_builtin_call_covered_with_work",
)
write_methods_match = re.search(r'method not in \{([^}]*)\}', resource_write_coverage)
assert write_methods_match, "resource-write replay collection method set is missing"
write_methods = set(re.findall(r'"([a-z_]+)"', write_methods_match.group(1)))
assert producer_methods == write_methods, (producer_methods, write_methods)
assert 'call_target.selection.include_nonassert_contract_calls and (kind == "requires" or proof_is_ensure_kind(kind))' in source_call_statements

scalar_call_purity_path = ROOT / "src/proof/replay/type_bound_scalar_call_purity.elisa"
scalar_call_purity = function_body(scalar_call_purity_path, "proof_replay_type_bound_scalar_call_source_pure")
assert scalar_call_purity.index("proof_replay_deterministic_analysis_context_ensure") < scalar_call_purity.index("proof_replay_resource_call_pure_function(report, cache.analysis_scratch")
assert "proof_replay_deterministic_call_alias_index_ensure" in scalar_call_purity
assert "proof_replay_deterministic_call_alias_imports_ensure" in scalar_call_purity
assert "entry.declaration, row, &cache.analysis_scratch" in scalar_call_purity

resource_lend_producer = function_body(ROOT / "src/proof/resources/call_region_lending.elisa", "proof_resource_call_lend_storage_is_confined")
assert "return_borrowed_view_free" in resource_lend_producer
assert "all_parameter_target_borrowed_view_free" in resource_lend_producer

function_collection = function_body(ROOT / "src/proof/check/function_index.elisa", "proof_collect_functions")
assert "proof_type_contains_borrowed_view_with_work" in function_collection
assert "all_parameter_target_borrowed_view_free" in function_collection
assert "return_borrowed_view_free" in function_collection

kernel_lend = function_body(ROOT / "src/proof/kernel_replay/resource_call_lend.elisa", "proof_kernel_replay_resource_lend")
assert "region_mapping_used.push(false)" in kernel_lend and "return false if not region_mapping_used[mapping_index]" in kernel_lend
kernel_fixture = (ROOT / "examples/kernel_resource_bootstrap_runtime.elisa").read_text(encoding="utf-8")
assert '"unused-region-mapping"' in kernel_fixture and "return 28 if proof_kernel_replay_resource_report" in kernel_fixture

# Return-marker coverage reuses the already built per-owner position index; each
# required source return still needs exactly one event at its exact parser offset.
owner_validator = function_body(resource_source_path, "proof_replay_resource_safety_owner_valid_with_work")
index_build = owner_validator.index("proof_replay_resource_binding_position_index_build_with_work(report, root, source_work)")
identity_check = owner_validator.index("proof_replay_resource_binding_identities_source_valid_with_work(report, root, resource_positions.index")
return_check = owner_validator.index("proof_replay_resource_return_markers_covered_indexed_with_work(report, root, resource_positions.index")
assert index_build < identity_check < return_check
return_coverage = function_body(ROOT / "src/proof/replay/resource_return_coverage.elisa", "proof_replay_resource_return_markers_covered_indexed_with_work")
assert 'proof_replay_resource_binding_position_kind_count_at_with_work(index, "resource-region-return", position.offset.usize(), source_work)' in return_coverage
assert "not markers.complete or markers.count != 1" in return_coverage
kind_count = function_body(ROOT / "src/proof/replay/resource_binding_identity_validation.elisa", "proof_replay_resource_binding_position_kind_count_at_with_work")
assert "while low < high" in kind_count and "index.offsets[middle] < offset" in kind_count
identity_position_find = function_body(ROOT / "src/proof/replay/resource_binding_identity_validation.elisa", "proof_replay_resource_binding_position_find_with_work")
for range_scan in (identity_position_find, kind_count):
    charge_line = "not proof_replay_owner_work_charge(1, source_work)"
    terminator = "break if index.offsets[current] != offset"
    assert charge_line in range_scan
    assert terminator in range_scan
    scan_start = range_scan.index("while current < index.offsets.count")
    assert range_scan.index(charge_line, scan_start) < range_scan.index(terminator)
assert "count <- count + 1 if index.kinds[current] == kind" in kind_count
assert "return (false, 0) if count > 1" in kind_count

checked_access = (ROOT / "src/proof/model/report_checked_access_inventory.elisa").read_text(encoding="utf-8")
assert all(expected in checked_access for expected in ("proof_report_source_work_charge(sview_len(attempt.name), source_work)", "proof_report_source_work_charge(sview_len(attempt.rule), source_work)", "proof_report_source_work_charge(sview_len(row.owner_name), source_work)", "proof_report_source_work_charge(sview_len(row.rule), source_work)"))
checked_access_admission = function_body(ROOT / "src/proof/model/report_structure_bound_failure.elisa", "proof_source_analysis_report_structure_bound_failure")
assert "proof_report_checked_access_coverage(source.file, report, source_work)" in checked_access_admission
assert 'return "source-checked-access-coverage" if not checked_accesses_covered' in checked_access_admission
checked_access_index_build = checked_access.split("def proof_checked_access_index_build(", 1)[1].split("def proof_checked_access_index_find(", 1)[0]
assert "return ProofCheckedAccessIndex{valid: false} if proof_checked_access_key_equal(prior, row.owner_name" in checked_access_index_build
checked_access_collector = function_body(ROOT / "src/proof/model/report_checked_access_inventory.elisa", "proof_checked_access_collect_expr")
checked_access_body = function_body(ROOT / "src/proof/model/report_checked_access_inventory.elisa", "proof_checked_access_collect_body")
checked_match_merge = "proof_checked_access_alias_merge_match_arm(entry_names, entry_values, alias_values, arm_names, arm_values, work)"
assert checked_access_collector.count(checked_match_merge) == 1
assert checked_access_body.count(checked_match_merge) == 1
match_merge = function_body(ROOT / "src/proof/model/report_checked_access_inventory.elisa", "proof_checked_access_alias_merge_match_arm")
assert "if proof_expr_equal(joined_values[index], entry_values[index]) and proof_expr_equal(arm_values[index], entry_values[index])" in match_merge
assert "if guard_effect.effectful:" in checked_access_body
assert "proof_checked_access_alias_invalidate_all(entry_names, entry_values, work)" in checked_access_body
alias_merge = function_body(ROOT / "src/proof/model/report_checked_access_inventory.elisa", "proof_checked_access_alias_merge_equal_indexes")
assert "if proof_expr_equal(then_values[index], else_values[index]):" in alias_merge
assert "alias_values[index] <- Ast::Expr.Invalid" in alias_merge, "a changed alias on a loop exit must fail the equality join"
while_branch = checked_access_body.split("Ast::Stmt.While(condition, nested, _):", 1)[1].split("Ast::Stmt.For(", 1)[0]
for_branch = checked_access_body.split("Ast::Stmt.For(_, variables, iterable, nested, _):", 1)[1].split("Ast::Stmt.Match(", 1)[0]
loop_join = "proof_checked_access_alias_merge_equal_indexes(alias_names, alias_values, entry_names, entry_values, loop_names, loop_values, work)"
assert loop_join in while_branch and loop_join in for_branch, "loop exits must join the body state with the zero-iteration state"
exit_alias_invalidation = "transfer.found and not proof_checked_access_alias_invalidate_all(loop_names, loop_values, work)"
assert exit_alias_invalidation in while_branch and exit_alias_invalidation in for_branch, "loop transfers must not retain body aliases across a possibly early exit"
assert "not transfer.complete" in while_branch and "not transfer.complete" in for_branch, "loop-flow scanning remains bounded and fail-closed"
loop_flow = (ROOT / "src/proof/model/report_checked_access_loop_flow.elisa").read_text(encoding="utf-8")
control_expr_transfer = function_body(
    ROOT / "src/proof/model/report_checked_access_loop_flow.elisa",
    "proof_checked_access_control_expr_has_recovery_transfer",
)
assert "Ast::Expr.GetElse(value, recovery, _)" in control_expr_transfer
assert "proof_checked_access_loop_has_exit_transfer(recovery, work, depth + 1, nested_loops)" in control_expr_transfer
assert "Ast::Expr.Binary(left, _, right, _)" in control_expr_transfer
loop_exit_transfer = function_body(
    ROOT / "src/proof/model/report_checked_access_loop_flow.elisa",
    "proof_checked_access_loop_has_exit_transfer",
)
assert "Ast::Stmt.If(condition, yes, no, _):" in loop_exit_transfer
assert "proof_checked_access_control_expr_has_recovery_transfer(condition, work, depth + 1, nested_loops)" in loop_exit_transfer
assert "Ast::Stmt.Expr(expression, _):" in loop_exit_transfer
assert "Ast::Stmt.VarDecl(_, type_expression, value, _):" in loop_exit_transfer
assert "Ast::Stmt.Assign(target, _, value, _):" in loop_exit_transfer
for control_branch in ("Ast::Stmt.If(condition, yes, no, _):", "Ast::Stmt.While(condition, nested, _):", "Ast::Stmt.For(_, variables, iterable, nested, _):"):
    branch = checked_access_body.split(control_branch, 1)[1]
    branch = branch.split("Ast::Stmt.", 1)[0]
    assert "proof_checked_access_control_expr_has_recovery_transfer" in branch
    assert "recovery_transfer.found and not proof_checked_access_alias_invalidate_all" in branch
assert "return (false, false)" in control_expr_transfer, "unhandled or over-budget control expressions fail closed"
checked_access_lines = checked_access_collector.splitlines()
row_push_indices = [index for index, line in enumerate(checked_access_lines) if "rows.push(ProofCheckedAccessSource{" in line]
assert row_push_indices, "the source census must bound each collected checked-access row"
for index in row_push_indices:
    assert index > 0 and "rows.count >= PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT / 4" in checked_access_lines[index - 1], checked_access_lines[max(0, index - 1):index + 1]
checked_access_coverage = checked_access.split("def proof_report_checked_access_coverage(", 1)[1]
for coverage_rule in ("Ast::expr_pos(attempt.goal)", "found.row >= seen.count", "seen[found.row] <- true", "or not present"):
    assert coverage_rule in checked_access_coverage
assert "return false if not found.complete or not found.found or found.row >= seen.count" in checked_access_coverage
assert "return false if seen[found.row]" not in checked_access_coverage, "repeated evaluations of one checked source occurrence are allowed"
print("resource replay preserves storage/marker checks and source-bounds checked-access attempts")
