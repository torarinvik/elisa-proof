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
for protocol in ("Eq", "Ord", "Less", "Add", "Sub", "Mul", "Div", "Neg", "BitAnd", "BitOr", "BitXor"):
    assert f'"{protocol}"' in all_ops
assert "proof_replay_variant_type_operator_impl_exists_with_work(element, protocol, report, work)" in all_ops
assert "not implementation.complete or implementation.exists" in all_ops
assert "proof_replay_type_bound_local_work_charge(1, work)" in all_ops

order_ops = function_body(LOCAL_FACTS, "proof_replay_type_bound_order_comparisons_trusted_with_work")
assert 'protocols: darray[sview] = ["Ord", "Less"]' in order_ops
assert "not implementation.complete or implementation.exists" in order_ops

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
assert 'if protocol == "Ord":' in variant_ops
assert 'proof_replay_variant_builtin_operator_impl_exists_with_work(report, name, "Less", source_work)' in variant_ops

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
assert "proof_replay_control_expr_position_equal(trace.expression, lower)" in loop_range
assert "proof_replay_control_expr_position_equal(trace.expression, upper)" in loop_range

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
