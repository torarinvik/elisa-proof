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
resource_scalar_guard = function_body(resource_purity_path, "proof_replay_resource_call_scalar_type_with_work")
assert "proof_replay_resource_scalar_type_with_work(expression, report, source_work, 0)" in resource_scalar_guard
assert "not scalar.complete or not scalar.scalar" in resource_scalar_guard
assert "proof_replay_control_match_guard_scalar_type(expression)" in resource_scalar_guard
resource_purity_function = function_body(resource_purity_path, "proof_replay_resource_call_pure_function")
assert "proof_structural_typed_operator_statements_have_overload(body, parameters, declaration_line, operator_source, 0, entry.owner, true)" in resource_purity_function
assert "or overloaded_operator" in resource_purity_function
resource_name_counts = function_body(ROOT / "src/proof/replay/resource_call_name_counts.elisa", "proof_replay_resource_call_name_counts_match")
assert "proof_replay_resource_call_name_is_irrelevant_with_work(report, operator_source" in resource_name_counts
resource_coverage = function_body(ROOT / "src/proof/replay/resource_call_site_validation.elisa", "proof_replay_resource_call_coverage_for_owner_with_work")
assert "proof_replay_resource_call_name_counts_match(cache.resource_call_owner_snapshots[located.row].source_calls, event_names, report, cache.scratch, cache.deterministic_calls.declaration_index, cache.deterministic_calls.alias_index, parameters, body, source_work)" in resource_coverage
assert "proof_replay_source_call_target_context(parameters, cache.scratch.source.source_annotations, &cache.scratch, entry.name, entry.owner, owner_line, owner_offset, source_work, true, true)" in resource_coverage
assert "proof_replay_source_calls_with_target_work(parameters, body, cache.scratch.source.source_annotations, &source_calls, call_target, source_work)" in resource_coverage
assert "call_target.selection.unresolved_dispatch_found" in resource_coverage

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

print("resource-call and return replay preserve source-bound storage and marker checks")
