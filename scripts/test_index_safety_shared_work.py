"""Keep short-circuit guard classification on the per-function source-work meter."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/check/index_safety_value.elisa").read_text()


def function_body(text: str, name: str) -> str:
    start = text.index(f"def {name}(")
    end = text.find("\n        def ", start + 1)
    return text[start:] if end < 0 else text[start:end]


helper = function_body(source, "proof_index_safety_expr_supported_with_work")
guard = function_body(source, "proof_check_index_safety_value")

assert "report.analysis_1.budgets.index_safety_source_work" in helper
assert "proof_expr_supported_with_work(expression, &support_work)" in helper
assert guard.count("proof_index_safety_expr_supported_with_work(") == 3
assert "condition_supported: bool = proof_index_safety_expr_supported_with_work(condition" in guard
assert "support_work: mutable usize = 0" not in guard
assert "proof_index_safety_preflight_expr_work(left, 5," in guard
assert "proof_index_safety_preflight_expr_work(right, 5," in guard

print("index-safety source-work guards passed")
