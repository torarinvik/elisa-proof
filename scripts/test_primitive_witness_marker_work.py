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
