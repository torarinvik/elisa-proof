#!/usr/bin/env python3
"""Ensure source replay independently checks overloaded scalar operator semantics."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LOCAL_FACTS = ROOT / "src/proof/replay/type_bound_local_facts.elisa"


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    signature = re.compile(rf"^\s*def {re.escape(name)}\s*\(")
    for start, line in enumerate(lines):
        if signature.match(line):
            indent = len(line) - len(line.lstrip())
            end = start + 1
            while end < len(lines):
                current = lines[end]
                if current.strip() and len(current) - len(current.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[start:end])
    raise AssertionError(f"missing {name}")


all_ops = function_body(LOCAL_FACTS, "proof_replay_type_bound_scalar_element_operators_trusted_with_work")
assert "proof_replay_variant_type_operator_protocols_absent_with_work(element, protocols, report, work)" in all_ops
assert "operators.complete and operators.absent" in all_ops
assert '["Eq", "Ord", "Less", "Add", "Sub", "Mul", "Div", "Neg", "BitAnd", "BitOr", "BitXor"]' in all_ops

order_ops = function_body(LOCAL_FACTS, "proof_replay_type_bound_order_comparisons_trusted_with_work")
assert 'protocols: darray[sview] = ["Ord", "Less"]' in order_ops
assert "proof_replay_variant_type_operator_protocols_absent_with_work(element, protocols, report, work)" in order_ops

for name in (
    "proof_replay_type_bound_local_array_witness_with_work",
    "proof_replay_type_bound_parameter_array_fact",
    "proof_replay_type_bound_local_array_fact_with_work",
):
    body = function_body(LOCAL_FACTS, name)
    marker = body.index("proof_scalar_element_marker(root, 1, position, element_width)")
    assert "proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, element, work)" in body[marker:]
    assert "proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, element, work)" in body[marker:]

variant_ops = function_body(ROOT / "src/proof/replay/variant_exclusion_validation.elisa", "proof_replay_variant_type_operator_impl_exists_with_work")
assert 'if protocol == "Ord":' not in variant_ops
assert 'proof_replay_variant_builtin_operator_impl_exists_with_work(report, name, "Less", source_work)' not in variant_ops
assert "proof_replay_variant_scope_positions_build(report, source_work)" in variant_ops
assert "proof_replay_variant_free_operator_mask_with_work(report, scope_index_status.index, report.source.source_declarations, source_work, 0)" in variant_ops
assert "proof_replay_variant_scoped_operator_exists_with_index(report, scope_index_status.index, name, wanted_mask, source_work)" in variant_ops
assert "return (false, false) if names.count == 0" in variant_ops
batch_ops = function_body(ROOT / "src/proof/replay/variant_exclusion_validation.elisa", "proof_replay_variant_type_operator_protocols_absent_with_work")
assert "return (false, false) if names.count == 0" in batch_ops
assert batch_ops.count("proof_replay_variant_operator_scope_snapshot_with_work(report, source_work)") == 1
protocol_mask_builder = function_body(ROOT / "src/proof/replay/variant_exclusion_validation.elisa", "proof_replay_variant_operator_protocol_mask_with_work")
assert "for protocol in protocols" in protocol_mask_builder
assert "proof_replay_variant_scoped_operator_exists_with_index(report, snapshot.index, name, wanted.mask, source_work)" in batch_ops
named_batch_ops = function_body(ROOT / "src/proof/replay/variant_exclusion_validation.elisa", "proof_replay_variant_named_operator_protocols_absent_with_work")
assert named_batch_ops.count("proof_replay_variant_operator_scope_snapshot_with_work(report, source_work)") == 1
assert "proof_replay_variant_operator_protocol_mask_with_work(protocols, source_work)" in named_batch_ops
assert "proof_replay_variant_scoped_operator_exists_with_index(report, snapshot.index, concrete, wanted.mask, source_work)" in named_batch_ops
variant_source = (ROOT / "src/proof/replay/variant_exclusion_validation.elisa").read_text(encoding="utf-8")
assert "proof_replay_variant_builtin_operator_impl_exists_with_work" not in variant_source
enum_scalar = function_body(ROOT / "src/proof/replay/type_bound_field_enum_validation.elisa", "proof_replay_type_bound_const_enum_field_scalar_with_work")
assert "proof_replay_variant_type_and_named_operator_protocols_absent_with_work(enum_type, path[path.count - 1], protocols, report, work)" in enum_scalar
combined_enum_ops = function_body(ROOT / "src/proof/replay/variant_exclusion_validation.elisa", "proof_replay_variant_type_and_named_operator_protocols_absent_with_work")
assert combined_enum_ops.count("proof_replay_variant_operator_scope_snapshot_with_work(report, source_work)") == 1
alias_scan = function_body(ROOT / "src/proof/replay/type_bound_shorthand_validation.elisa", "proof_replay_type_bound_shorthand_alias_operator_scan")
assert alias_scan.count("proof_replay_variant_scope_positions_build(report, source_work)") == 1
assert alias_scan.count("proof_replay_variant_free_operator_mask_with_work(report, scope_index.index, report.source.source_declarations, source_work, 0)") == 1
alias_scan_indexed = function_body(ROOT / "src/proof/replay/type_bound_shorthand_validation.elisa", "proof_replay_type_bound_shorthand_alias_operator_scan_with_index")
assert "proof_replay_variant_scoped_operator_exists_with_index(report, index, alias_name, wanted_mask, source_work)" in alias_scan_indexed
scoped_operator_lookup = function_body(ROOT / "src/proof/replay/variant_exclusion_validation.elisa", "proof_replay_variant_scoped_operator_exists_with_index")
operator_scope_source = ROOT / "src/proof/replay/variant_exclusion_operator_scope.elisa"
scope_source_text = operator_scope_source.read_text(encoding="utf-8")
scope_is_impl = function_body(operator_scope_source, "proof_replay_variant_scope_is_impl_with_work")
assert "proof_replay_variant_scope_position_at_with_work(index, position.line, position.offset, source_work)" in scope_is_impl
assert "row.annotation_marker_count == 1" in scope_is_impl
free_mask = function_body(operator_scope_source, "proof_replay_variant_free_operator_mask_with_work")
assert "proof_replay_variant_scope_is_impl_with_work(report, index, position, source_work)" in free_mask
assert "if scope_kind.is_impl:" in free_mask
assert "mask <- mask | path_scope.global_operator_mask" in free_mask
assert "continue" in free_mask
assert "PROOF_REPLAY_VARIANT_OPERATOR_ALL_FLAGS" in free_mask
assert "proof_source_operator_dunder_mask" not in scope_source_text
scope_masks = function_body(operator_scope_source, "proof_replay_variant_scope_body_operator_masks")
assert "self_mask <- self_mask | dunder_mask" in scope_masks
assert "explicit_receiver_mask <- explicit_receiver_mask | dunder_mask" in scope_masks
assert "global_mask <- global_mask | dunder_mask if not receiver_known" in scope_masks
assert "Ast::Decl.Extern(name" in scope_masks
assert "global_mask <- global_mask | proof_replay_variant_operator_dunder_mask(name)" in scope_masks
scope_index_build = function_body(operator_scope_source, "proof_replay_variant_scope_positions_build")
assert 'annotation.owner == "__impl_scope"' in scope_index_build
assert 'annotation.owner == "__ext_concrete"' in scope_index_build
assert "not scope_row.complete or not scope_row.found" in scope_index_build
assert "row.annotation_marker_count != 0" in scope_index_build
assert "return (false, index) if row.annotation_marker_count != 0" in scope_index_build
assert "impl_owner_complete" in scope_index_build and "extension_owner_complete" in scope_index_build
assert "concrete_count: mutable usize" in scope_index_build
assert "proof_name_hash(row.annotation_concrete)" in scope_index_build
assert "bucket_size: usize = concrete_bucket_sizes[slot] + 1" in scope_index_build
assert "bucket_size > PROOF_REPLAY_VARIANT_SCOPE_MAX_BUCKET" in scope_index_build
assert "while entry < chain_count and visits < PROOF_REPLAY_VARIANT_SCOPE_MAX_BUCKET" in scoped_operator_lookup
assert "index.concrete_hashes[entry] == hash" in scoped_operator_lookup
assert "index.concrete_next_indices[entry]" in scoped_operator_lookup
assert "scope.self_operator_mask" in scoped_operator_lookup
assert 'scope.annotation_owner, "__ext_concrete", source_work' in scoped_operator_lookup
assert 'scope.annotation_owner != "__ext_concrete"' in scoped_operator_lookup
assert "receiver_mask: usize = path_scope.self_operator_mask" in scoped_operator_lookup
assert "path_scope.explicit_receiver_mask if path_scope.explicit_receiver_type == concrete" in scoped_operator_lookup
assert "(receiver_mask & wanted_mask) != 0" in scoped_operator_lookup
variant_replay = ROOT / "src/proof/replay/variant_exclusion_validation.elisa"
variant_mask_source = ROOT / "src/proof/replay/variant_operator_masks.elisa"
replay_entry = (ROOT / "src/proof/replay.elisa").read_text(encoding="utf-8")
assert replay_entry.index('include "./replay/variant_operator_masks.elisa"') < replay_entry.index('include "./replay/variant_exclusion_validation.elisa"')
variant_text = variant_replay.read_text(encoding="utf-8") + variant_mask_source.read_text(encoding="utf-8")
assert "proof_source_operator_dunder_mask" not in variant_text
assert "proof_source_operator_mask_for_protocol" not in variant_text
dunder_mask = function_body(variant_mask_source, "proof_replay_variant_operator_dunder_mask")
for dunder, flag in (
    ("__eq__", "EQUALITY"), ("__cmp__", "ORDERING"), ("__add__", "ADDITION"),
    ("__sub__", "SUBTRACTION"), ("__mul__", "MULTIPLICATION"),
    ("__div__", "DIVISION"), ("__neg__", "NEGATION"),
):
    assert f'if name == "{dunder}": return PROOF_REPLAY_VARIANT_OPERATOR_{flag}_FLAG' in dunder_mask
protocol_mask = function_body(variant_mask_source, "proof_replay_variant_operator_mask_for_protocol")
for protocol, flag in (
    ('"Eq"', "EQUALITY"), ('"Ord" | "Less"', "ORDERING"), ('"Add"', "ADDITION"),
    ('"Sub"', "SUBTRACTION"), ('"Mul"', "MULTIPLICATION"),
    ('"Div"', "DIVISION"), ('"Neg"', "NEGATION"),
):
    assert f'{protocol} -> PROOF_REPLAY_VARIANT_OPERATOR_{flag}_FLAG' in protocol_mask

counting_loop = function_body(ROOT / "src/proof/replay/type_bound_validation.elisa", "proof_replay_type_bound_counting_loop_fact")
assert "variables.count != 1" in counting_loop
assert "low_value >= 0 and high_value >= low_value and high_value < 2147483647" in counting_loop
assert 'i32_type: Ast::Expr = Ast::Expr.Ident("i32", position)' in counting_loop
assert counting_loop.count("proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, i32_type, work)") == 2
assert "proof_scalar_term_marker(binder, position)" in counting_loop
assert "proof_signed_place_marker(binder, 32, position)" in counting_loop
assert "return false" in counting_loop

loop_range = function_body(ROOT / "src/proof/replay/boundary_loop_fact_sources.elisa", "proof_replay_control_loop_range_source_with_work")
assert "proof_source_expression_has_overloaded_operator(iterable, report.source.source_operator_protocol_mask, 0)" in loop_range
assert "proof_replay_control_stable_expression(report, trace, low, source_work)" in loop_range
assert "proof_replay_control_stable_expression(report, trace, high, source_work)" in loop_range
assert "proof_replay_summary_expr_equal_with_limit(trace.expression, lower, source_work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in loop_range
assert "proof_replay_trace_expression_positions_equal_with_work(trace.expression, lower, 0, &source_work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in loop_range
assert "proof_replay_summary_expr_equal_with_limit(trace.expression, upper, source_work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in loop_range
assert "proof_replay_trace_expression_positions_equal_with_work(trace.expression, upper, 0, &source_work, PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT)" in loop_range

for name in (
    "proof_replay_type_bound_local_array_witness_with_work",
    "proof_replay_type_bound_local_array_fact_with_work",
):
    body = function_body(LOCAL_FACTS, name)
    assert 'proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, Ast::Expr.Ident("usize", position), work)' in body
    assert "proof_scalar_term_marker(count, position)" in body
    assert "proof_unsigned_place_marker(count, ElisaProofKernelCore::PROOF_KERNEL_MACHINE_WORD_BITS, position)" in body
    assert "if count_fact_match:" in body or "if count_matches != 0:" in body

parameter_fact = function_body(LOCAL_FACTS, "proof_replay_type_bound_parameter_fact")
assert parameter_fact.count("proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, parameter.type_expression, work)") >= 3
assert parameter_fact.count("proof_replay_type_bound_order_comparisons_trusted_with_work(report, parameter.type_expression, work)") >= 4
local_scalar_fact = function_body(LOCAL_FACTS, "proof_replay_type_bound_local_scalar_fact_with_work")
assert local_scalar_fact.count("proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, local_type, work)") >= 3
assert local_scalar_fact.count("proof_replay_type_bound_order_comparisons_trusted_with_work(report, local_type, work)") >= 4

constant_lookup = function_body(ROOT / "src/proof/replay/type_bound_validation.elisa", "proof_replay_type_bound_scalar_constant_lookup")
assert "proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, candidate_type, work)" in constant_lookup
call_result = function_body(ROOT / "src/proof/replay/type_bound_call_result.elisa", "proof_replay_type_bound_call_result_fact_with_work")
assert "Ast::Expr.Field(object_expression, field_name, _)" in call_result
assert "projected_field <- field_name" in call_result
assert "proof_replay_type_bound_tuple_projection_type_with_work(return_type, report.source.source_annotations, projected_field, work)" in call_result
assert "result_type <- projection.element" in call_result
for marker_check in (
    'proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, result_type, work)',
):
    assert call_result.count(marker_check) >= 3
tuple_projection = function_body(ROOT / "src/proof/replay/type_bound_tuple_projection.elisa", "proof_replay_type_bound_tuple_projection_type_with_work")
assert 'annotation.owner, "__tuple_label"' in tuple_projection
assert "candidates != 1" in tuple_projection
assert "prior == found" in tuple_projection
assert "selected_count != 1" in tuple_projection
entry_count = function_body(ROOT / "src/proof/replay/entry_count_boundary_validation.elisa", "proof_replay_entry_count_boundary_fact_valid_with_work")
assert 'proof_replay_type_bound_scalar_element_operators_trusted_with_work(report, Ast::Expr.Ident("usize", position), source_work)' in entry_count
assert 'proof_replay_type_bound_order_comparisons_trusted_with_work(report, Ast::Expr.Ident("usize", position), source_work)' in entry_count

print("scalar and range witnesses: source replay gates overloaded scalar semantics and order facts")
