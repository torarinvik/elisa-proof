"""Pin the context-local, read-only marker decode cache used by scalar-witness queries.

This source-level query-plan guard is not a runtime timing claim. Proof reports,
proven/replay outcomes, and adversarial forged-marker refusals remain the runtime
acceptance criteria.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "src/proof/kernel_replay"
if not __debug__:
    raise SystemExit("run without Python -O; operation-count assertions are acceptance checks")


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
    cache_builder = function_body(congruence, "proof_kernel_replay_witness_marker_cache")
    candidate = function_body(marker_source, "proof_kernel_replay_witness_marker_candidate")
    marker_names = function_body(marker_source, "proof_kernel_replay_witness_marker_name")
    budget = function_body(congruence, "proof_kernel_replay_scalar_term_witnessed_budget")
    element_budget = function_body(congruence, "proof_kernel_replay_scalar_element_remaining_budget")

    # Decode each candidate through the existing strict readers once, then pass this
    # query-local immutable record array through recursion and both comparison operands.
    assert len(re.findall(r"proof_kernel_replay_witness_marker_cache\s*\(", scalar_wrapper)) == 1
    assert len(re.findall(r"proof_kernel_replay_witness_marker_cache\s*\(", primitive)) == 1
    assert "for fact in facts" in cache_builder
    assert "proof_kernel_replay_witness_marker_candidate(nodes, fact)" in cache_builder
    for reader in (
        "proof_kernel_replay_untrusted_operator_marker",
        "proof_kernel_replay_marker_argument",
        "proof_kernel_replay_unsigned_marker_info",
        "proof_kernel_replay_element_marker",
    ):
        assert len(re.findall(rf"{reader}\s*\(", cache_builder)) == 1, reader
        assert reader not in budget and reader not in element_budget
    assert "fact >= nodes.count" in candidate and 'nodes[fact].kind != "call"' in candidate
    assert "callee >= nodes.count" in candidate and 'nodes[callee].kind == "ident"' in candidate
    expected_markers = {
        "__elisa_untrusted_operator_type",
        "__elisa_primitive_scalar_type",
        "__elisa_unsigned_type_bound",
        "__elisa_primitive_scalar_element",
    }
    assert set(re.findall(r'"(__elisa_[a-z_]+)"', marker_names)) == expected_markers

    # The cache carries parsed payloads only, not a proof result, and its lifetime
    # is the local query: recursive calls reuse it; no cache lives in a workspace.
    assert "darray[ProofKernelReplayWitnessMarker]" in scalar_wrapper
    assert "darray[ProofKernelReplayWitnessMarker]" in primitive
    assert "markers" in budget and "for fact in facts" not in budget
    assert "markers" in element_budget and "for fact in facts" not in element_budget
    assert "proof_kernel_replay_scalar_term_witnessed_budget(nodes, children, markers" in budget
    assert "proof_kernel_replay_scalar_element_remaining_budget(nodes, children, markers" in budget

    # The paired path retains the independent per-operand depth budget and the
    # left-to-right `and` short circuit while sharing only decoded marker records.
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

    # Early depth/budget rejection occurs before cache construction.
    assert "return false if not ElisaProofKernelCore::depth_valid(depth) or depth >= PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH" in scalar_wrapper
    assert "return false if not ElisaProofKernelCore::depth_valid(0) or PROOF_KERNEL_REPLAY_CONGRUENCE_SCAN_DEPTH == 0" in primitive
    print("scalar witness query cache: exact marker readers are decoded once per immutable query context")


if __name__ == "__main__":
    main()
