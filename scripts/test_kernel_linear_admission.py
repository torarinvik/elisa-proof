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
assert inconsistent.count("proof_kernel_replay_witness_marker_cache_fill_with_work") == 1
assert "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work" in inconsistent
assert "proof_kernel_replay_primitive_comparison_with_markers_with_work" in inconsistent
complementary = body(refutation, "proof_kernel_replay_facts_order_complementary_with_work")
assert complementary.count("proof_kernel_replay_witness_marker_cache_fill_with_work") <= 1
assert "markers_ready: mutable bool = false" in complementary
assert "proof_kernel_replay_readable_order_with_markers_and_work" in complementary
assert "&markers, &markers_ready" in complementary

collector = body(ROOT / "src/proof/kernel_replay/term_arithmetic.elisa", "proof_kernel_replay_collect_bounds_with_work")
and_branch = collector.index('if node.operator == "and":')
and_return = collector.index("                return", and_branch)
comparison = collector.index("proof_kernel_replay_collect_bound_comparison_with_goal_work")
assert and_branch < and_return < comparison
assert "\n            proof_kernel_replay_collect_bound_comparison_with_goal_work" in collector

print("linear replay: operator roots, primitive operands, and unsigned widths are admitted exactly")
