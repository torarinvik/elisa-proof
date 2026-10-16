#!/usr/bin/env python3
"""Keep the i64 finite-model backend aligned with admitted source arithmetic."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
model_path = ROOT / "src/proof/kernel_replay/goal_metered_bounded_model.elisa"
unsigned_path = ROOT / "src/proof/kernel_replay/unsigned_bounds.elisa"
producer_signed_path = ROOT / "src/proof/linear/fixed_width_arithmetic_safety_work.elisa"
producer_unsigned_path = ROOT / "src/proof/linear/witnessed_expressions.elisa"
producer_helpers_path = ROOT / "src/proof/linear/bounds_and_markers_integrated_helpers.elisa"


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


integer_model = body(model_path, "proof_kernel_replay_model_int_with_goal_work")
unsupported_refusal = integer_model.index('return empty if node.operator in {"<<", ">>", "&", "|", "^"}')
binary_dispatch = integer_model.index('if node.kind == "binary":')
left_eval = integer_model.index("left: ProofKernelReplayInt =", binary_dispatch)
assert binary_dispatch < unsupported_refusal < left_eval
assert 'return proof_kernel_replay_shift_safe' not in integer_model
for bitwise in ('if node.operator == "&"', 'if node.operator == "|"', 'if node.operator == "^"'):
    assert bitwise not in integer_model

fragment = body(model_path, "proof_kernel_replay_bounded_model_fragment_with_goal_work")
comparison_fragment = fragment.split('if node.operator in {"==", "!=", "<", ">", "<=", ">="}:', 1)[1].split("            false", 1)[0]
assert "PROOF_KERNEL_REPLAY_WITNESS_UNTRUSTED_OPERATOR" in comparison_fragment
assert "proof_kernel_replay_untrusted_operator_applies_with_work" in comparison_fragment
assert comparison_fragment.index("proof_kernel_replay_untrusted_operator_applies_with_work") < comparison_fragment.index("proof_kernel_replay_scalar_term_witnessed_budget_with_work")

overloaded_fixture = (ROOT / "examples/rejected_bounded_model_overloaded_equality.elisa").read_text(encoding="utf-8")
assert "impl Eq for i64" in overloaded_fixture
assert "return self != other" in overloaded_fixture
assert "ensure result == true" in overloaded_fixture
assert "return value == value" in overloaded_fixture

bounded_goal = body(model_path, "proof_kernel_replay_bounded_model_goal_with_goal_work")
marker_goal_guard = body(model_path, "proof_kernel_replay_goal_contains_type_marker_with_work")
assert marker_goal_guard.index('if node.kind == "call":') < marker_goal_guard.index("proof_kernel_replay_type_marker_callee_with_goal_work(nodes, children, root, work_used)")
assert "proof_kernel_replay_type_marker_callee_with_goal_work(nodes, children, root, work_used)" in marker_goal_guard
assert "proof_kernel_replay_goal_contains_type_marker_with_work(nodes, children, node.left" in marker_goal_guard
assert "proof_kernel_replay_goal_contains_type_marker_with_work(nodes, children, node.right" in marker_goal_guard
assert bounded_goal.index("proof_kernel_replay_goal_contains_type_marker_with_work(nodes, children, goal_root") < bounded_goal.index("proof_kernel_replay_bounded_model_fragment_with_goal_work(nodes, children, facts")
assert "metadata, not logical propositions" in model_path.read_text(encoding="utf-8")
marker_truth_sites = []
for source in (ROOT / "src/proof/kernel_replay").glob("*.elisa"):
    if "ProofKernelReplayBool{known: true, value: true} if marker" in source.read_text(encoding="utf-8"):
        marker_truth_sites.append(source)
assert marker_truth_sites == [model_path], marker_truth_sites
fact_model_helpers = (ROOT / "src/proof/kernel_replay/fact_model_integrated_helpers.elisa").read_text(encoding="utf-8")
for legacy_pin_helper in (
    "proof_kernel_replay_term_pin(",
    "proof_kernel_replay_pinned_constant(",
    "proof_kernel_replay_collect_constant_pins(",
    "proof_kernel_replay_cached_pinned_constant(",
    "proof_kernel_replay_constant_int_with_pins(",
    "proof_kernel_replay_operand_matches_through_pins(",
):
    assert legacy_pin_helper not in fact_model_helpers, legacy_pin_helper
portable_forgery = (ROOT / "scripts/tests/portable_replay_kernel_forgeries.py").read_text(encoding="utf-8")
assert 'forged_disjunction = append_node(marker_goal, "binary", "or", unsigned_bound, subject_is_zero)' in portable_forgery
assert '"hypotheses": [signed_bound, subject_is_one]' in portable_forgery
width_preflight = bounded_goal.index("proof_kernel_replay_unsigned_report_safe_with_goal_work(nodes, children, facts, goal_root, work_used)")
frame_enumeration = bounded_goal.index("proof_kernel_replay_model_frame_nodes_with_goal_work")
assert width_preflight < frame_enumeration
assert bounded_goal.count("proof_kernel_replay_unsigned_report_safe_with_goal_work(") == 1
assert bounded_goal.count("proof_kernel_replay_bounded_model_fragment_with_goal_work(nodes, children, facts") == 2
assert "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in bounded_goal[width_preflight:frame_enumeration]
assert "proof_kernel_replay_signed_expression_safe_with_bounds_goal_work" in body(
    unsigned_path, "proof_kernel_replay_unsigned_report_safe_with_goal_work"
)
assert "proof_kernel_replay_unsigned_expression_safe_with_cached_markers_and_goal_work" in body(
    unsigned_path, "proof_kernel_replay_unsigned_report_safe_with_goal_work"
)
unsigned_safety = body(unsigned_path, "proof_kernel_replay_unsigned_expression_safe_with_replay_work")
# Machine shifts require a proven count interval within the left operand's actual
# width. A bound valid for i64 does not automatically validate an i8/u8 shift.
shared_safety_path = ROOT / "src/proof/kernel_replay/goal_metered_unsigned_widening.elisa"
shared_safety = body(shared_safety_path, "proof_kernel_replay_signed_expression_safe_with_bounds_goal_cached_work")
shift_check = shared_safety.split('if node.operator == "<<" or node.operator == ">>":', 1)[1].split("if width == 0:", 1)[0]
assert "shift_width: i64 = width if width != 0 else unsigned_width" in shift_check
assert "not shift_count.has_lower or not shift_count.has_upper" in shift_check
assert "shift_count.lower < 0" in shift_check
assert "shift_count.upper >= shift_width" in shift_check
assert shared_safety.index("shift_count.upper >= shift_width") < shared_safety.index("if width == 0:")
unsigned_shift = unsigned_safety.split('if node.operator == "<<" or node.operator == ">>":', 1)[1].split("# A guarded unsigned subtraction", 1)[0]
assert "shift_count.upper >= width" in unsigned_shift
assert unsigned_safety.index("return true if width == 0") < unsigned_safety.index("shift_count.upper >= width")
report_safety = body(unsigned_path, "proof_kernel_replay_unsigned_report_safe_with_goal_work")
assert "proof_kernel_replay_signed_expression_safe_with_bounds_goal_work(nodes, children, fact" in report_safety
assert "proof_kernel_replay_signed_expression_safe_with_bounds_goal_work(nodes, children, root" in report_safety
assert "not unsigned_safe or not signed_safe" in report_safety
conditional_gate = unsigned_safety.index('if node.kind == "if":')
shortcut = unsigned_safety.index("proof_kernel_replay_unsigned_conditional_difference_safe_with_goal_work", conditional_gate)
shortcut_accept = unsigned_safety.index("return true if conditional_safe", shortcut)
branch_checks = unsigned_safety.index("then_signed_width:", conditional_gate)
assert conditional_gate < branch_checks < shortcut < shortcut_accept
assert unsigned_safety.index("then_signed_width != 0 and else_unsigned_width != 0", branch_checks) < shortcut
producer_helper = body(producer_helpers_path, "proof_fixed_width_if_branch_sorts_compatible_with_work")
for conflict in (
    "then_signed != 0 and then_unsigned != 0",
    "else_signed != 0 and else_unsigned != 0",
    "then_signed != 0 and else_unsigned != 0",
    "then_unsigned != 0 and else_signed != 0",
    "then_signed != 0 and else_signed != 0 and then_signed != else_signed",
    "then_unsigned != 0 and else_unsigned != 0 and then_unsigned != else_unsigned",
):
    assert conflict in producer_helper
producer_signed = body(producer_signed_path, "proof_signed_expression_safe_with_bounds_work_inner_scaled")
producer_unsigned = body(producer_unsigned_path, "proof_unsigned_expression_safe_inner_work")
assert "proof_fixed_width_if_branch_sorts_compatible_with_work" in producer_signed
assert "proof_fixed_width_if_branch_sorts_compatible_with_work" in producer_unsigned

overflow_fixture = (ROOT / "examples/signed_overflow_bounded_model.elisa").read_text(encoding="utf-8")
assert "signed_square_wraps_in_model_domain" in overflow_fixture
assert "signed_square_bounded_safe" in overflow_fixture
runtime_regression = (ROOT / "scripts/test.d/03-index-and-loop-facts.sh").read_text(encoding="utf-8")
assert "signed_overflow_bounded_model.elisa" in runtime_regression
assert 'not functions["signed_square_wraps_in_model_domain"]["verified"]' in runtime_regression
assert 'not f["counterexample_found"]' in runtime_regression
assert "rejected_bounded_model_overloaded_equality.elisa" in runtime_regression

print("kernel finite model: source-width preflight, overloaded operator refusal, and type-marker goal rejection are guarded")
