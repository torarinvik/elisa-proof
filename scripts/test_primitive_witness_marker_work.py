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
        "proof_kernel_replay_comparison_root_untrusted_with_work",
    )

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
