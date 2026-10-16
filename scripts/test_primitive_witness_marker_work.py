"""Static regression for metered, fail-closed scalar witness marker decoding.

This deliberately checks source structure only. Runtime refusal still requires a proof
binary built from the current proof/compiler source revisions.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "src/proof/kernel_replay"


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
    raise AssertionError(f"missing function {name} in {path}")


def main() -> None:
    facts = REPLAY / "witness_marker_facts.elisa"
    scalar = REPLAY / "scalar_witness_work.elisa"
    candidate = function_body(facts, "proof_kernel_replay_witness_marker_candidate_with_work")
    classify = function_body(facts, "proof_kernel_replay_witness_marker_kind_with_work")
    fill = function_body(scalar, "proof_kernel_replay_witness_marker_cache_fill_with_work")
    comparison = function_body(
        REPLAY / "order_and_sign_integrated_helpers.elisa",
        "proof_kernel_replay_primitive_comparison_with_markers_with_work",
    )
    root_classification = function_body(
        REPLAY / "order_and_sign_integrated_helpers.elisa",
        "proof_kernel_replay_comparison_root_untrusted_with_markers_and_work",
    )
    core = function_body(ROOT / "src/proof/kernel_core.elisa", "proof_kernel_unsigned_width_valid")
    unsigned_marker = function_body(
        REPLAY / "scalar_witness_work.elisa",
        "proof_kernel_replay_unsigned_marker_info_with_work",
    )
    element_apply = function_body(scalar, "proof_kernel_replay_untrusted_element_operator_applies_with_work")
    reference_apply = function_body(scalar, "proof_kernel_replay_untrusted_scalar_reference_operator_applies_with_work")
    comparison = (REPLAY / "order_and_sign_integrated_helpers.elisa").read_text(encoding="utf-8")
    bounded_model = (REPLAY / "goal_metered_bounded_model.elisa").read_text(encoding="utf-8")
    logical_join = (REPLAY / "logical_join_identity.elisa").read_text(encoding="utf-8")
    source_witnesses = (ROOT / "src/proof/check/operator_witnesses.elisa").read_text(encoding="utf-8")
    operator_queries = ROOT / "src/proof/check/operator_witness_queries.elisa"
    operator_operand = function_body(operator_queries, "proof_runtime_operator_operand_untrusted")
    operator_expression = function_body(operator_queries, "proof_runtime_operator_expression_witnessed_with_work")
    enum_parenthesis_helpers = (
        (operator_queries, "proof_const_enum_shorthand_has_builtin_equality_with_work", "const_enum_builtin"),
        (ROOT / "src/proof/check/plain_enum_equality.elisa", "proof_plain_enum_member_has_builtin_equality_with_work", "plain_enum_builtin"),
    )
    runtime_support = ROOT / "src/proof/check/runtime_support_and_calls.elisa"
    bounded_parenthesis_classifiers = (
        (runtime_support, "proof_statement_region_new_call_supported"),
    )
    operator_expression_gate = function_body(
        ROOT / "src/proof/check/runtime_support_and_calls.elisa",
        "proof_expr_has_unmodeled_operator_with_work",
    )

    # Resolving a source-call return type can traverse a large alias/declaration
    # tree. Keep that classification on the same source-work meter as the other
    # operator witness lookups, and refuse classification if it exhausts the cap.
    call_return_type = operator_operand.split(
        "if called_index < functions.returns.return_types.count:", 1
    )[1].split("called: sview = proof_callable_name(callee)", 1)[0]
    assert "proof_builtin_operator_type_name_with_work(" in call_return_type
    assert "&source_work) can Global.Read" in call_return_type
    assert "report.source_types.source_effect_index.work.implicit_effect_work <- source_work" in call_return_type
    assert "return true if source_work > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT" in call_return_type
    assert "proof_builtin_operator_type_name(" not in operator_operand
    extern_gate = operator_operand.split(
        "if (proof_float_mode can Global.Read) and imported < functions.externs.extern_signatures.count:",
        1,
    )[1].split("\n                    return true", 1)[0]
    assert "source_function_exists: mutable bool = called_index < functions.lookup.source.names.count" in extern_gate
    assert "proof_function_name_lookup_with_work(functions, called, &source_work)" in extern_gate
    assert "report.source_types.source_effect_index.work.implicit_effect_work <- source_work" in extern_gate
    assert "return true if not source_function.complete" in extern_gate
    assert "source_function.row < functions.lookup.source.names.count" in extern_gate
    assert "proof_resource_function_name_count(functions, called)" not in operator_operand
    assert extern_gate.index("source_function_exists: mutable bool") < extern_gate.index("signature: ProofExternSignature")

    # A depth-limited witness walk must never turn an unvisited suffix into a
    # trusted builtin operand. Marker decoders poison the shared budget, the
    # operand query fails closed, and its expression caller rejects no-witness.
    for helper_name in (
        "proof_builtin_operator_term_witnessed_with_work",
        "proof_index_operator_term_witnessed_with_work",
        "proof_builtin_index_expression_witnessed_with_work",
    ):
        helper = function_body(operator_queries, helper_name)
        depth_refusal = helper.split(
            "if depth >= PROOF_ANALYSIS_RECURSION_DEPTH_LIMIT:", 1
        )[1].split("match expression:", 1)[0]
        assert "work <- limit + 1" in depth_refusal and "return false" in depth_refusal
    operand_work_check = operator_operand.index(
        "return true if work > PROOF_MATCH_LOWERING_WORK_LIMIT"
    )
    operand_depth_check = operator_operand.index(
        "return true if depth >= PROOF_ANALYSIS_RECURSION_DEPTH_LIMIT"
    )
    operand_shape_walk = operator_operand.index("match expression:")
    assert operand_work_check < operand_depth_check < operand_shape_walk
    expression_depth_refusal = operator_expression.split(
        "if depth >= PROOF_ANALYSIS_RECURSION_DEPTH_LIMIT:", 1
    )[1].split("match expression:", 1)[0]
    assert "work <- PROOF_MATCH_LOWERING_WORK_LIMIT + 1" in expression_depth_refusal
    assert "return false" in expression_depth_refusal
    expression_witness_gate = (
        "not (proof_runtime_operator_expression_witnessed_with_work("
        "expression, facts, report, functions, 0, work) can Global.Read)"
    )
    assert expression_witness_gate in operator_expression_gate

    # Enum admission peels parenthesized operands before the outer operator walk.
    # Keep that peel inside the same bounded source-work accounting and make deep
    # syntax poison the shared meter so callers fail closed.
    for path, helper_name, result_name in enum_parenthesis_helpers:
        helper = function_body(path, helper_name)
        assert "depth: usize = 0" in helper.splitlines()[0]
        assert "proof_type_audit_work_charge(1, source_work)" in helper
        refusal = helper.split("if depth >= PROOF_TYPE_AUDIT_DEPTH_LIMIT:", 1)[1].split("return false if not", 1)[0]
        assert "source_work <- PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT + 1" in refusal
        assert "depth + 1" in helper
        call = operator_operand.index(f"{result_name}: bool = {helper_name}(")
        exhausted = operator_operand.index("return true if source_work > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT", call)
        if result_name == "plain_enum_builtin":
            result = operator_operand.index(result_name, exhausted)
        else:
            result = operator_operand.index(f"return false if {result_name}", call)
        assert exhausted < result

    # Simple shape classifiers can run before the general bounded AST walk.
    # Keep their parenthesis-only recursion capped so hostile syntax cannot exhaust
    # the producer stack even when the classifier itself has no mutable work meter.
    for path, helper_name in bounded_parenthesis_classifiers:
        helper = function_body(path, helper_name)
        assert "depth: usize = 0" in helper.splitlines()[0]
        assert "return false if depth >= PROOF_ANALYSIS_RECURSION_DEPTH_LIMIT" in helper
        assert "depth + 1" in helper

    terminal_classifier = function_body(runtime_support, "proof_expression_terminal_with_depth")
    assert "-> (complete: bool, terminal: bool)" in terminal_classifier.splitlines()[0]
    assert "return (false, false) if depth >= PROOF_ANALYSIS_RECURSION_DEPTH_LIMIT" in terminal_classifier
    assert "proof_expression_terminal_with_depth(inner, depth + 1)" in terminal_classifier
    return_contracts = (ROOT / "src/proof/check/returns/contracts.elisa").read_text(encoding="utf-8")
    terminal_check = return_contracts.index("terminal_classification: (complete: bool, terminal: bool)")
    terminal_failure = return_contracts.index("if not terminal_classification.complete:", terminal_check)
    terminal_use = return_contracts.index("terminal_expression: bool = terminal_classification.terminal", terminal_check)
    assert terminal_check < terminal_failure < terminal_use
    terminal_failure_body = return_contracts[terminal_failure:terminal_use]
    assert 'proof_add_finding(report, "expression-unsupported"' in terminal_failure_body
    assert "flow.valid <- false" in terminal_failure_body and "flow.normal <- false" not in terminal_failure_body
    saturation = (ROOT / "src/proof/replay/source_binding_validation/for_saturation.elisa").read_text(encoding="utf-8")
    assert "not terminal_classification.complete or not terminal_classification.terminal" in saturation
    saturation_statement = saturation.index("Ast::Stmt.Expr(terminal, _):")
    summary_charge = saturation.index("not proof_replay_summary_expr_charge_with_work(terminal, source_work)", saturation_statement)
    terminal_query = saturation.index("proof_expression_terminal_with_depth(terminal, 0)", saturation_statement)
    assert summary_charge < terminal_query

    # Invalid fact/callee references and exhausted name scans are incomplete, never
    # interpreted as an ordinary non-marker fact.
    assert "return (false, 0) if fact >= nodes.count" in candidate
    assert "return (false, 0) if callee >= nodes.count" in candidate
    assert "proof_kernel_replay_witness_marker_kind_with_work(nodes[callee].name" in candidate
    assert "return false if not marker_candidate.complete" in fill
    assert "return false if not proof_kernel_replay_scalar_witness_charge" in fill

    markers = (
        "__elisa_untrusted_operator_type",
        "__elisa_primitive_scalar_type",
        "__elisa_primitive_integer_type",
        "__elisa_unsigned_type_bound",
        "__elisa_primitive_scalar_element",
    )
    for marker in markers:
        assert marker in classify

    # The host integer range 8..64 is not the set of supported unsigned widths.
    # Keep producer and replay marker decoding on the same explicit width set.
    for width in (
        "PROOF_KERNEL_U8_WIDTH",
        "PROOF_KERNEL_U16_WIDTH",
        "PROOF_KERNEL_U32_WIDTH",
        "PROOF_KERNEL_MACHINE_WORD_BITS",
    ):
        assert width in core
    assert "ensure result ==" in core
    assert "proof_kernel_unsigned_width_valid(width_work.value)" in unsigned_marker
    # Keep validated unsigned widths separate from scalar-element path depth in the cache.
    assert "kind: PROOF_KERNEL_REPLAY_WITNESS_UNSIGNED_TYPE, root: marker.name_root, depth: 0, width: marker.width" in fill
    assert "name: sview" in (REPLAY / "witness_marker_facts.elisa").read_text(encoding="utf-8")
    assert "name: nodes[marker.name_root].name" in fill
    unsigned_width_lookup = function_body(
        REPLAY / "goal_metered_conditional_plans.elisa",
        "proof_kernel_replay_unsigned_width_from_markers_with_goal_work",
    )
    assert 'if marker.name == "":' in unsigned_width_lookup
    assert "work_used <- PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT + 1" in unsigned_width_lookup
    assert "proof_kernel_replay_goal_search_text_equal(marker.name, name, work_used)" in unsigned_width_lookup
    for path, function, mismatch, selected_width in (
        (REPLAY / "goal_metered_conditional_plans.elisa", "proof_kernel_replay_unsigned_width_from_markers_with_goal_work", "marker.width != width", "width <- marker.width if width == 0"),
        (REPLAY / "goal_metered_linear_disequality.elisa", "proof_kernel_replay_linear_place_marker_width_with_work", "value.value != width", "width <- value.value if width == 0"),
        (REPLAY / "goal_metered_linear_disequality.elisa", "proof_kernel_replay_linear_element_width_with_work", "marker.width != width", "width <- marker.width if width == 0"),
    ):
        width_lookup = function_body(path, function)
        assert mismatch in width_lookup
        assert "work_used <- PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT + 1" in width_lookup
        assert selected_width in width_lookup
    # The interval and linear unsigned-name paths now share this collision check
    # through their marker-snapshot wrappers.
    for path, function in (
        (REPLAY / "goal_metered_interval.elisa", "proof_kernel_replay_unsigned_marker_width_for_name_with_goal_work"),
        (REPLAY / "goal_metered_linear_disequality.elisa", "proof_kernel_replay_linear_unsigned_marker_width_from_markers_with_work"),
    ):
        assert "proof_kernel_replay_unsigned_width_from_markers_with_goal_work" in function_body(path, function)
    # Indexed container markers require an indexed path. Element.Ref applies to the
    # exact reference and every single-index read rooted there, including dynamic indexes.
    assert "subscripts.count == 0" in element_apply
    assert "Element.Ref" in fill
    scalar_reference_branch = source_witnesses.split("if scalar_reference.known and not scalar_reference_is_owner_generic:", 1)[1].split("builtin_type:", 1)[0]
    assert '"Element.Ref"' in scalar_reference_branch
    assert "proof_add_untrusted_scalar_element_operator_witness_with_work" in scalar_reference_branch
    assert "proof_kernel_replay_scalar_witness_expr_equal(nodes, children, marked_reference, term" in reference_apply
    for consumer in (comparison, bounded_model, logical_join):
        assert "PROOF_KERNEL_REPLAY_WITNESS_UNTRUSTED_SCALAR_REFERENCE_OPERATOR" in consumer or 'marker.protocol == "Element.Ref"' in consumer
        assert "proof_kernel_replay_untrusted_scalar_reference_operator_applies_with_work" in consumer
    assert "subscripts.count != 1" in reference_apply
    assert "same_reference" in reference_apply
    assert "constant_int_remaining_with_work_limit" not in reference_apply
    for reader in (
        "proof_kernel_replay_untrusted_operator_marker_with_work",
        "proof_kernel_replay_marker_argument_with_work",
        "proof_kernel_replay_unsigned_marker_info_with_work",
        "proof_kernel_replay_element_marker_with_work",
    ):
        assert reader in fill
    # Each reserved marker parser rejects malformed payloads instead of silently
    # dropping them from the query-local cache.
    assert fill.count("return false if not marker.known") >= 5
    assert "markers.push" in fill
    # Every cached marker is visited for every primitive comparison. Charge before
    # skipping trusted marker kinds so repeated comparisons cannot hide O(markers)
    # scans outside the caller's shared replay budget.
    marker_loop = comparison.index("for marker in markers")
    marker_charge = comparison.index("proof_kernel_replay_goal_search_charge(work_used)", marker_loop)
    marker_skip = comparison.index("continue if marker.kind", marker_loop)
    assert marker_loop < marker_charge < marker_skip
    assert "or work_used > work_limit" in comparison[marker_charge:marker_skip]
    root_loop = root_classification.index("for marker in markers")
    root_charge = root_classification.index("proof_kernel_replay_goal_search_charge(work_used)", root_loop)
    root_skip = root_classification.index("continue if marker.kind", root_loop)
    assert root_loop < root_charge < root_skip
    assert "or work_used > work_limit" in root_classification[root_charge:root_skip]
    print("scalar witness markers: metered classification and malformed-marker refusal are guarded")


if __name__ == "__main__":
    main()
