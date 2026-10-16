#!/usr/bin/env python3
"""Keep linear replay and fixed-width markers inside admitted primitive semantics."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            end = index + 1
            while end < len(lines):
                following = lines[end]
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[index:end])
    raise AssertionError(f"missing {name} in {path}")


core = ROOT / "src/proof/kernel_core.elisa"
widths = body(core, "proof_kernel_unsigned_width_valid")
for width in ("PROOF_KERNEL_U8_WIDTH", "PROOF_KERNEL_U16_WIDTH", "PROOF_KERNEL_U32_WIDTH", "PROOF_KERNEL_MACHINE_WORD_BITS"):
    assert width in widths
assert "width >=" not in widths and "width <=" not in widths

producer = ROOT / "src/proof/linear/bounds_and_markers.elisa"
for function in (
    "proof_unsigned_exact_term_marker_info",
    "proof_element_marker_info",
    "proof_unsigned_marker_info",
):
    assert "proof_kernel_unsigned_width_valid" in body(producer, function), function

kernel = ROOT / "src/proof/kernel_replay"
facade = (ROOT / "src/proof/kernel_replay.elisa").read_text(encoding="utf-8")
assert facade.index('include "./kernel_replay/linear_unsigned_width_index.elisa"') < facade.index('include "./kernel_replay/goal_metered_linear_disequality.elisa"')
assert facade.index('include "./kernel_replay/goal_metered_linear_disequality.elisa"') < facade.index('include "./kernel_replay/goal_metered_linear_unsigned_width.elisa"') < facade.index('include "./kernel_replay/goal_metered_linear_certificates.elisa"')
width_index_path = kernel / "linear_unsigned_width_index.elisa"
width_index_build = body(width_index_path, "proof_kernel_replay_linear_unsigned_width_index_build")
assert "marker.kind != PROOF_KERNEL_REPLAY_WITNESS_UNSIGNED_TYPE" in width_index_build
assert "marker.width)" in width_index_build
assert "index.conflicts[current] <- index.conflicts[current] or index.widths[current] != marker.width" in width_index_build
assert "PROOF_KERNEL_REPLAY_INDEX_MAX_CLUSTER" in width_index_build
width_index_lookup = body(width_index_path, "proof_kernel_replay_linear_unsigned_width_index_lookup")
assert "index.slots.count != index.capacity" in width_index_lookup
assert 'index.conflicts[row]' in width_index_lookup
assert "PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT + 1" in width_index_lookup
width_query = body(kernel / "goal_metered_linear_unsigned_width.elisa", "proof_kernel_replay_linear_unsigned_width_query_with_work")
assert "if not proof_kernel_replay_goal_bool_ref_value(index_ready):" in width_query
assert "proof_kernel_replay_linear_unsigned_width_index_build(markers, work_used)" in width_query
assert "proof_kernel_replay_linear_unsigned_width_index_lookup(width_index, node.name, work_used)" in width_query
width_wrapper = body(kernel / "goal_metered_linear_disequality.elisa", "proof_kernel_replay_linear_unsigned_width_with_work")
assert "index_ready: mutable bool = false" in width_wrapper
assert "proof_kernel_replay_linear_unsigned_width_query_with_work(nodes, children, root, facts, markers, &index, &index_ready" in width_wrapper
for path, function in (
    (kernel / "goal_metered_interval.elisa", "proof_kernel_replay_unsigned_marker_info_with_goal_work"),
    (kernel / "goal_metered_linear_disequality.elisa", "proof_kernel_replay_element_marker_with_goal_work"),
    (kernel / "scalar_witness_work.elisa", "proof_kernel_replay_unsigned_marker_info_with_work"),
):
    assert "proof_kernel_unsigned_width_valid" in body(path, function), function

disequality = body(kernel / "goal_metered_linear_disequality.elisa", "proof_kernel_replay_linear_fact_parts_with_work")
assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in disequality
assert "relation_admission.untrusted" in disequality
assert "proof_kernel_replay_primitive_comparison_with_markers_with_work" in disequality

linear_marker = body(kernel / "goal_metered_linear_disequality.elisa", "proof_kernel_replay_linear_marker_with_work")
assert linear_marker.index("return false if root >= nodes.count") < linear_marker.index("nodes[root].kind")
assert "root >= nodes.count or nodes[root]" not in linear_marker
linear_argument = body(kernel / "goal_metered_linear_certificates.elisa", "proof_kernel_replay_linear_argument_with_goal_work")
assert "not proof_kernel_replay_child_range_valid(call.children_start, call.children_count, children.count) or offset >= call.children_count" in linear_argument
assert linear_argument.index("not slot.known or slot.value >= nodes.count") < linear_argument.index("nodes[slot.value]")
assert "argument.kind != \"call_arg\" or argument.name != \"\" or argument.secondary_name != \"\"" in linear_argument
assert "argument.left >= nodes.count or not proof_kernel_replay_valid(nodes, argument.left)" in linear_argument

pruning = body(kernel / "goal_metered_linear_pruning.elisa", "proof_kernel_replay_linear_prune_with_goal_work")
assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in pruning
assert "relation_admission.untrusted" in pruning
assert "proof_kernel_replay_primitive_comparison_with_markers_with_work" in pruning

chain = body(kernel / "goal_metered_comparison_chain.elisa", "proof_kernel_replay_chain_equal_other_with_work")
assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in chain
assert "proof_kernel_replay_primitive_comparison_with_markers_with_work" in chain

join_identity = body(kernel / "logical_join_identity.elisa", "proof_kernel_replay_logical_join_identity_with_work")
assert 'proof_kernel_replay_goal_search_text_equal(nodes[root].operator, "==", work_used)' in join_identity
assert "proof_kernel_replay_comparison_root_untrusted_with_work" in join_identity

equality = body(ROOT / "src/proof/replay/name_equality_closure.elisa", "proof_replay_equality_scalar_name_witnessed")
assert "ElisaProofKernelCore::proof_kernel_unsigned_width_valid(width.value)" in equality

refutation = kernel / "arithmetic_refutation.elisa"
inconsistent = body(refutation, "proof_kernel_replay_facts_arithmetically_inconsistent_with_work")
assert inconsistent.count("proof_kernel_replay_witness_marker_cache_fill_with_work") == 2
assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in inconsistent
assert "proof_kernel_replay_primitive_comparison_with_markers_with_work" in inconsistent
complementary = body(refutation, "proof_kernel_replay_facts_order_complementary_with_work")
assert complementary.count("proof_kernel_replay_witness_marker_cache_fill_with_work") <= 1
assert "markers_ready: mutable bool = false" in complementary
assert "proof_kernel_replay_readable_order_with_markers_and_work" in complementary
assert "&markers, &markers_ready" in complementary

distinct = body(kernel / "goal_metered_distinct_disequality.elisa", "proof_kernel_replay_distinct_disequality_disjunction_with_goal_work")
assert distinct.count("proof_kernel_replay_witness_marker_cache_fill_with_work") == 1
assert "proof_kernel_replay_signed_disequality_constant_with_goal_work(nodes, children, facts, markers," in distinct
assert "proof_kernel_replay_unsigned_disequality_constant_with_goal_work(nodes, children, facts, markers," in distinct
for function in (
    "proof_kernel_replay_signed_disequality_constant_with_goal_work",
    "proof_kernel_replay_unsigned_disequality_constant_with_goal_work",
):
    reader = body(kernel / "goal_metered_distinct_disequality.elisa", function)
    assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in reader
    assert "proof_kernel_replay_primitive_comparison_with_markers_with_work" in reader

fact_inconsistency = kernel / "goal_metered_fact_inconsistency.elisa"
inconsistent_node = body(fact_inconsistency, "proof_kernel_replay_fact_inconsistent_node_with_goal_work")
assert "markers: mutable darray[ProofKernelReplayWitnessMarker]&" in inconsistent_node
assert "markers_ready: mutable bool&" in inconsistent_node
assert "if not proof_kernel_replay_goal_bool_ref_value(markers_ready):" in inconsistent_node
assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in inconsistent_node
assert "proof_kernel_replay_witness_marker_cache_fill_with_work" in inconsistent_node
assert "not admission.complete or admission.untrusted" in inconsistent_node
assert "proof_kernel_replay_fact_negated_constant_comparison_with_goal_work(nodes, children, markers," in inconsistent_node
facts_inconsistent = body(fact_inconsistency, "proof_kernel_replay_facts_inconsistent_with_goal_work")
assert "markers_ready: mutable bool = false" in facts_inconsistent
assert "proof_kernel_replay_fact_inconsistent_node_with_goal_work(nodes, children, roots, markers, markers_ready," in facts_inconsistent

summary = body(kernel / "fact_model_integrated_helpers.elisa", "proof_kernel_replay_fact_proves_call_summary_with_work")
assert "markers_ready: mutable bool = false" in summary
assert "if not markers_ready:" in summary
assert "proof_kernel_replay_witness_marker_cache_fill_with_work" in summary
assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in summary
assert "proof_kernel_replay_comparison_root_untrusted_with_work" not in summary

collector = body(ROOT / "src/proof/kernel_replay/term_arithmetic.elisa", "proof_kernel_replay_collect_bounds_with_work")
and_branch = collector.index('if node.operator == "and":')
and_return = collector.index("                return", and_branch)
comparison = collector.index("proof_kernel_replay_collect_bound_comparison_with_goal_work")
assert and_branch < and_return < comparison
assert "\n            proof_kernel_replay_collect_bound_comparison_with_goal_work" in collector

goal_depth = body(ROOT / "src/proof/linear/congruence_goal_depth.elisa", "proof_goal_depth")
operator_guard = goal_depth.index(
    "arithmetic_guard_safe: bool = proof_source_arithmetic_operator_guard_with_work(goal, facts, operator_mask, budget, exhausted)"
)
equality_literal_shortcut = goal_depth.index(
    "proof_disjunction_comparison_from_equality_literal_with_work(left, operator, right, facts, budget, exhausted)"
)
assert operator_guard < equality_literal_shortcut, (
    "comparison equality-literal reasoning must reject source-overloaded facts first"
)

goal_admission = body(ROOT / "src/proof/model/report_goal_admission.elisa", "proof_report_goal_source_admissible_after_structure_internal")
assert goal_admission.index("proof_source_expression_has_overloaded_operator_with_work(attempt.goal, source_operator_mask") < goal_admission.index("proof_source_assert_by_goal_attempt_admitted")
assert "report.source.source_primitive_operator_mask" not in (ROOT / "src/proof/model/report_goal_admission.elisa").read_text(encoding="utf-8")
source_masks = body(ROOT / "src/proof/model/checked_view.elisa", "proof_source_analysis_operator_mask_from_source")
assert "proof_source_primitive_operator_overloaded_with_work(annotations, source_work)" in source_masks
assert "mask: mutable usize = PROOF_SOURCE_OPERATOR_MASK_EMPTY" in source_masks
assert "proof_source_operator_mask_with_generic_bounds(annotations, mask, source_work)" in source_masks
declaration_mask = body(ROOT / "src/proof/model/checked_view.elisa", "proof_source_analysis_operator_declaration_mask")
assert "mask <- mask | proof_source_operator_dunder_mask(name)" in declaration_mask
unknown_declaration = declaration_mask.split("                    _:\n", 1)[1]
assert "return false" in unknown_declaration
index_masks = body(ROOT / "src/proof/check/source_operator_guard.elisa", "proof_source_operator_masks_from_index")
assert "proof_source_operator_mask_with_generic_bounds(report.source.source_annotations, PROOF_SOURCE_OPERATOR_MASK_EMPTY, source_work)" in index_masks
source_snapshot = body(ROOT / "src/proof/model/checked_view_admission.elisa", "proof_source_analysis_goal_admission_snapshot")
assert "not source.source_operator_masks_valid" in source_snapshot
assert "source.source_primitive_operator_mask" in source_snapshot
source_bound = body(ROOT / "src/proof/model/report_structure_bound_failure.elisa", "proof_source_analysis_report_structure_bound_failure")
assert 'return "source-operator-mask" if not source.source_operator_masks_valid' in source_bound
assert "report.source.source_primitive_operator_mask != source.source_primitive_operator_mask" in source_bound
assert "report.source.source_operator_protocol_mask != source.source_operator_protocol_mask" in source_bound

print("linear replay: operator roots, primitive operands, widths, and equality facts are admitted exactly")
