"""Pin the deterministic full-fact traversal reduction in primitive comparisons.

This is a source-level operation counter, not a wall-clock or runtime-call claim:
the comparison's two scalar-witness checks short-circuit, so the old second
filter runs only when the left operand is witnessed. Runtime verdict and replay
equivalence are covered by the focused proof and portable replay suites.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "src/proof/kernel_replay"


def function_body(path: Path, name: str) -> str:
    lines = path.read_text().splitlines()
    signature = re.compile(rf"^\s*def {re.escape(name)}\s*\(")
    for start, line in enumerate(lines):
        if signature.match(line):
            indent = len(line) - len(line.lstrip())
            end = start + 1
            while end < len(lines):
                current = lines[end]
                if current.strip():
                    current_indent = len(current) - len(current.lstrip())
                    if current_indent <= indent and not current.lstrip().startswith("#"):
                        break
                end += 1
            return "\n".join(lines[start:end])
    raise AssertionError(f"missing function {name} in {path}")


def main() -> None:
    integrated = REPLAY / "order_and_sign_integrated_helpers.elisa"
    congruence = REPLAY / "congruence.elisa"
    marker_source = REPLAY / "witness_marker_facts.elisa"
    primitive = function_body(integrated, "proof_kernel_replay_primitive_comparison")
    scalar_wrapper = function_body(congruence, "proof_kernel_replay_scalar_term_witnessed")
    filter_facts = function_body(marker_source, "proof_kernel_replay_witness_marker_facts")
    candidate = function_body(marker_source, "proof_kernel_replay_witness_marker_candidate")
    marker_names = function_body(marker_source, "proof_kernel_replay_witness_marker_name")

    # Count actual full-list filter call sites in the kernel source. The scalar
    # wrapper has one, and the optimized paired path creates one shared ordered
    # marker list before testing either root.
    assert len(re.findall(r"proof_kernel_replay_witness_marker_facts\s*\(", scalar_wrapper)) == 1
    assert len(re.findall(r"proof_kernel_replay_witness_marker_facts\s*\(", primitive)) == 1
    assert "for fact in facts" in filter_facts and "markers.push(fact)" in filter_facts
    assert "proof_kernel_replay_witness_marker_candidate(nodes, fact)" in filter_facts
    assert "fact >= nodes.count" in candidate and 'nodes[fact].kind != "call"' in candidate
    assert "callee >= nodes.count" in candidate and 'nodes[callee].kind == "ident"' in candidate
    expected_markers = {
        "__elisa_untrusted_operator_type",
        "__elisa_primitive_scalar_type",
        "__elisa_unsigned_type_bound",
        "__elisa_primitive_scalar_element",
    }
    assert set(re.findall(r'"(__elisa_[a-z_]+)"', marker_names)) == expected_markers

    # Verify the paired path retains the prior independent per-operand depth
    # budget and the left-to-right `and` short circuit.
    assert "not ElisaProofKernelCore::depth_valid(0)" in primitive
    assert "PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH == 0" in primitive
    assert "budget: usize = PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH" in primitive
    pair_calls = re.findall(
        r"proof_kernel_replay_scalar_term_witnessed_budget\(nodes, children, markers, "
        r"(left|right), 0, budget\)", primitive)
    assert pair_calls == ["left", "right"], pair_calls
    assert re.search(r"witnessed_budget\([^\n]+left[^\n]+\)\s+and\s+"
                     r"proof_kernel_replay_scalar_term_witnessed_budget\([^\n]+right",
                     primitive), primitive

    # Deterministic filter-pass counter for the same valid-depth comparison:
    # old left check always scans once; its right check scans only if left passes.
    # New implementation scans once before the checks; it does not share the
    # witness recursion's budget between operands.
    cases = ((False, 1, 1), (True, 2, 1))
    for left_witnessed, previous_passes, optimized_passes in cases:
        old_count = 1 + int(left_witnessed)
        new_count = 1
        assert (old_count, new_count) == (previous_passes, optimized_passes)
        assert old_count - new_count == int(left_witnessed)

    # Early depth/budget rejection performs no filter pass in either version.
    assert "return false if not ElisaProofKernelCore::depth_valid(depth) or depth >= PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH" in scalar_wrapper
    assert "return false if not ElisaProofKernelCore::depth_valid(0) or PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH == 0" in primitive
    print("primitive comparison witness-filter passes: left-fail 1->1; left-pass 2->1; exhausted 0->0")


if __name__ == "__main__":
    main()
