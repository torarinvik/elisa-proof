"""Keep overloaded indexed reads opaque until replay carries builtin type evidence."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"def {re.escape(name)}(?:\[[^\]]+\])?\(", line.lstrip()):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following.strip())
            return "\n".join(body)
    raise AssertionError(f"function {name} not found in {path}")


dispatch = (ROOT / "src/proof/linear/congruence_goals.elisa").read_text(encoding="utf-8")
assert "proof_index_read_equality_goal(facts, goal" not in dispatch
replay_dispatch = (ROOT / "src/proof/kernel_replay/resource_model.elisa").read_text(encoding="utf-8")
assert "proof_kernel_replay_index_read_equality(nodes, children, facts, goal_root" not in replay_dispatch
producer_rule = function_body(ROOT / "src/proof/linear/index_read_equalities.elisa", "proof_index_read_equality_goal")
kernel_rule = function_body(ROOT / "src/proof/kernel_replay/index_read_equalities.elisa", "proof_kernel_replay_index_read_equality")
typed_rule = function_body(ROOT / "src/proof/kernel_replay/index_read_equalities.elisa", "proof_kernel_replay_typed_index_read_equality_with_work")
assert producer_rule.splitlines()[-1] == "return false"
assert kernel_rule.splitlines()[-1] == "return false"
assert "not same_receiver" in typed_rule
assert 'left_receiver.family not in {"container", "string"}' in typed_rule
assert "proof_kernel_replay_term_sort(nodes, children, environment, typing_index, goal.left" in typed_rule
assert "current <- proof_kernel_replay_index_element_sort(current, environment, typing_index, work)" in (
    ROOT / "src/proof/kernel_replay/proposition_typing.elisa"
).read_text(encoding="utf-8")
assert "return proof_kernel_replay_unknown_sort() if not receiver.known or receiver.family != \"container\"" in function_body(
    ROOT / "src/proof/kernel_replay/typing_binding_sort_helpers.elisa",
    "proof_kernel_replay_index_element_sort",
)
assert "proof_kernel_replay_integral_sort(left_index_sort)" in typed_rule
assert 'left_result_sort.family not in {"integer", "boolean", "character"}' in typed_rule
assert "reachable: mutable darray[usize] = [left.right]" in typed_rule
assert "edge_sort_states[fact_index]" in typed_rule
assert 'kind_is_binary and candidate.operator == "=="' in typed_rule
assert "proof_kernel_replay_primitive_comparison_with_markers_with_work(nodes, children, markers, candidate.left, candidate.right" in typed_rule
assert "edge_primitive_states.push(1 if primitive else 2)" in typed_rule
assert "continue if edge_primitive_states[fact_index] != 1" in typed_rule
assert "proof_kernel_replay_disjunction_stable_receivers_equal_with_work(nodes, left.left, right.left" in typed_rule
assert "proof_kernel_replay_goal_search_expr_equal(nodes, children, left.left, right.left" not in typed_rule
source_candidate = function_body(ROOT / "src/proof/replay/typed_postcondition_replay.elisa", "proof_replay_typed_index_read_goal_shape_candidate")
assert 'left_receiver.kind in {"ident", "field"}' in source_candidate
assert 'right_receiver.kind in {"ident", "field"}' in source_candidate
stable_receiver = function_body(ROOT / "src/proof/kernel_replay/disjunction_call_guard.elisa", "proof_kernel_replay_disjunction_stable_receivers_equal_with_work")
assert 'left.kind == "ident"' in stable_receiver
assert "left.kind != right.kind" in stable_receiver
assert 'left.name != "" and left.name == right.name' in stable_receiver
assert 'left.kind != "field" or left.name != right.name' in stable_receiver
assert 'left.kind == "paren"' not in stable_receiver
assert "not proof_kernel_replay_goal_search_charge(work_used)" in stable_receiver
assert "not proof_kernel_replay_valid(nodes, left_root) or not proof_kernel_replay_valid(nodes, right_root)" in stable_receiver
assert "not proof_kernel_replay_goal_search_charge_node_text(nodes, left_root, work_used)" in stable_receiver
assert "not proof_kernel_replay_goal_search_charge_node_text(nodes, right_root, work_used)" in stable_receiver
assert "not proof_kernel_replay_arena_shape_valid(nodes[left_root])" in stable_receiver
assert "not proof_kernel_replay_arena_shape_valid(nodes[right_root])" in stable_receiver
assert "depth >= ElisaProofKernelCore::PROOF_KERNEL_REPLAY_DEPTH_LIMIT" in stable_receiver
assert "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in stable_receiver
assert "proof_kernel_replay_disjunction_stable_receivers_equal_with_work(nodes, left.left, right.left" in stable_receiver
assert "proof_kernel_replay_disjunction_term_has_call_with_work(nodes, children, left.right" in typed_rule
assert "proof_kernel_replay_disjunction_term_has_call_with_work(nodes, children, right.right" in typed_rule
assert "proof_kernel_replay_disjunction_term_has_call_with_work(nodes, children, candidate.left" in typed_rule
assert "proof_kernel_replay_disjunction_term_has_call_with_work(nodes, children, candidate.right" in typed_rule
assert "proof_kernel_replay_disjunction_term_has_untrusted_operator_with_work(nodes, children, markers, left.right" in typed_rule
assert "proof_kernel_replay_disjunction_term_has_untrusted_operator_with_work(nodes, children, markers, candidate.left" in typed_rule
operator_scan = function_body(ROOT / "src/proof/kernel_replay/disjunction_call_guard.elisa", "proof_kernel_replay_disjunction_term_has_untrusted_operator_with_work")
assert "proof_kernel_replay_untrusted_operator_applies_with_work" in operator_scan
assert "PROOF_KERNEL_REPLAY_WITNESS_UNTRUSTED_ELEMENT_OPERATOR" in operator_scan
assert "proof_kernel_replay_disjunction_term_has_untrusted_operator_with_work(nodes, children, markers, node.left" in operator_scan
assert 'return (true, false) if node.kind in {"int", "typed-int", "bool", "float", "string", "char", "ident"}' in operator_scan
assert "sview_len(candidate.kind)" in typed_rule
assert "sview_len(candidate.operator)" in typed_rule
producer_markers = (ROOT / "src/proof/check/operator_impl_queries.elisa").read_text(encoding="utf-8")
scalar_gate = (ROOT / "src/proof/check/operator_witness_queries.elisa").read_text(encoding="utf-8")
kernel_scalar_gate = (ROOT / "src/proof/kernel_replay/scalar_witness_work.elisa").read_text(encoding="utf-8")
assert 'proof_untrusted_operator_marker(root, "All", position)' in producer_markers
assert "proof_untrusted_operator_marker_info(fact)" in scalar_gate
assert "proof_kernel_replay_untrusted_operator_marker_with_work" in kernel_scalar_gate
assert "proof_kernel_replay_untrusted_operator_applies_with_work" in kernel_scalar_gate
operator_marker_match = function_body(
    ROOT / "src/proof/kernel_replay/scalar_witness_work.elisa",
    "proof_kernel_replay_untrusted_operator_applies_with_work",
)
depth_refusal = operator_marker_match.split(
    "if depth >= PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH:", 1
)[1].split("return true if", 1)[0]
assert "work_used <- work_limit + 1" in depth_refusal and "return false" in depth_refusal
indexed_path = function_body(
    ROOT / "src/proof/kernel_replay/scalar_witness_work.elisa",
    "proof_kernel_replay_indexed_container_path_with_work",
)
indexed_depth_refusal = indexed_path.split(
    "if not ElisaProofKernelCore::depth_valid(depth) or depth >= PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH:", 1
)[1].split("return false if not proof_kernel_replay_valid", 1)[0]
assert "work_used <- work_limit + 1" in indexed_depth_refusal and "return false" in indexed_depth_refusal

# The byte-reference arithmetic classifier is a rejection gate. Depth, work, or
# pointee-sort uncertainty must not collapse to "not a byte pointer" and admit
# arithmetic after the other operand checks succeed.
byte_reference_gate = function_body(
    ROOT / "src/proof/kernel_replay/scalar_reference_typing.elisa",
    "proof_kernel_replay_byte_pointer_reference_remaining",
)
assert "return true if remaining <= 1 or depth >= PROOF_KERNEL_TYPING_DEPTH_LIMIT or root >= nodes.count" in byte_reference_gate
assert "return true if not reference_shape.known" in byte_reference_gate
assert "return false if not reference_shape.is_reference" in byte_reference_gate
assert "return true if not pointee_sort.known" in byte_reference_gate
arithmetic_gate = function_body(
    ROOT / "src/proof/kernel_replay/proposition_typing.elisa",
    "proof_kernel_replay_term_sort_remaining",
)
assert "proof_kernel_replay_byte_pointer_reference_remaining(nodes, children, environment, typing_index, node.left" in arithmetic_gate

assert "proof_expr_equal" not in producer_rule
assert "proof_kernel_replay_expr_equal" not in kernel_rule
assert not any(line.startswith("for ") for line in producer_rule.splitlines() + kernel_rule.splitlines())

positive = (ROOT / "examples/index_read_equality.elisa").read_text(encoding="utf-8")
negative = (ROOT / "examples/rejected_index_read_equality.elisa").read_text(encoding="utf-8")
typed_positive = (ROOT / "examples/typed_index_read_congruence.elisa").read_text(encoding="utf-8")
overloaded_negative = (ROOT / "examples/rejected_typed_index_read_overloaded_equality.elisa").read_text(encoding="utf-8")
overloaded_index_negative = (ROOT / "examples/rejected_typed_index_read_overloaded_index.elisa").read_text(encoding="utf-8")
assert "def indexed_disequality_at_equal_index" in positive
assert "requires rows[cursor] != 64\n    ensure rows[3] != 64" in positive
assert "def indexed_disequality_from_negated_equality" in positive
assert "def indexed_read_at_transitively_equal_index" in positive
assert "requires first == middle\n    requires middle == last\n    ensure rows[first] == rows[last]" in typed_positive
assert "def typed_field_read_equal_at_index(store: TypedIndexReadStore&, cursor: i64)" in typed_positive
assert "ensure store.rows[cursor] == store.rows[3]" in typed_positive
assert "requires not (rows[cursor] == 64)\n    ensure rows[3] != 64" in positive
assert "def rejected_disequality_different_index" in negative
assert "def rejected_index_read_through_cross_sort_edges" in negative
assert "impl Eq for i64:" in overloaded_negative
assert "return self != other" in overloaded_negative
assert "def rejected_implicit_scalar_reference_overloaded_reflexivity(value: i64&) -> i64:" in overloaded_negative
assert "ensure value == value" in overloaded_negative
assert "def rejected_explicit_scalar_reference_overloaded_reflexivity(value: i64&) -> i64:" in overloaded_negative
assert "ensure value[0] == value[0]" in overloaded_negative
assert "def rejected_array_element_overloaded_equality(values: array[i64, 8]&" in overloaded_negative
assert "requires first == second\n    ensure values[first] == values[second]" in overloaded_negative
assert "def rejected_pure_call_result_overloaded_reflexivity(value: i64) -> i64:" in overloaded_negative
assert "ensure pure_i64_value(value) == pure_i64_value(value)" in overloaded_negative
assert "requires first == middle\n    requires middle == last\n    ensure rows[first] == rows[last]" in overloaded_negative
assert "impl Index for Box:" in overloaded_index_negative
assert "def __index__(self: Box&, index: i64) -> i64&:" in overloaded_index_negative
assert "ensure box[first] == box[last]" in overloaded_index_negative
assert "requires rows[cursor] != 64\n    ensure rows[3] != 64" in negative
runtime = (ROOT / "scripts/test_index_read_equality.py").read_text(encoding="utf-8")
assert '"index_read_equality.elisa", "failed"' in runtime
assert '"typed_index_read_congruence.elisa", "proved"' in runtime
assert '"typed_field_read_equal_at_index"' in runtime
assert '"open_indexed_prefix_reasoning.elisa", "failed"' in runtime
assert '"open_index_window_disjunctions.elisa", "failed"' in runtime
assert '"rejected_index_read_equality.elisa", "failed"' in runtime
assert '"rejected_typed_index_read_overloaded_equality.elisa", "failed"' in runtime
assert '"rejected_typed_index_read_overloaded_index.elisa", "failed"' in runtime
assert '"rejected_index_read_through_overloaded_equality"' in runtime
assert '"rejected_implicit_scalar_reference_overloaded_reflexivity"' in runtime
assert '"rejected_explicit_scalar_reference_overloaded_reflexivity"' in runtime
assert '"rejected_array_element_overloaded_equality"' in runtime
assert '"rejected_pure_call_result_overloaded_reflexivity"' in runtime
assert '"rejected_custom_index_congruence"' in runtime
assert '"rejected_disequality_different_index"' in runtime
assert '"rejected_index_read_through_cross_sort_edges"' in runtime

print("indexed-read transport is source-typed, transitive for exact-sort premises, and rejects coercive edges")
