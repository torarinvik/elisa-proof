#!/usr/bin/env python3
"""Keep proof-block call admission aligned with the caller's lexical scope."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
purity = (ROOT / "src/proof/check/proof_block_purity.elisa").read_text()
blocks = (ROOT / "src/proof/check/block_checker_and_patterns.elisa").read_text()
functions = (ROOT / "src/proof/check/function_checks.elisa").read_text()
fixture = (ROOT / "examples/rejected_impure_proof.elisa").read_text()
runtime_regression = (ROOT / "scripts/test_impure_proof_body.py").read_text()

assert "proof_assertion_calls_are_total_pure(expression: Ast::Expr, functions: mutable ProofFunctionTable&, caller_names: darray[sview]&, match_work_used: mutable usize&)" in purity
assert "proof_expression_has_opaque_callable_call_with_work(expression, functions, caller_names, 0, match_work_used)" in purity
assert "proof_purity_match_budget_check(report, name, position.line, work)" in purity
assert "proof_callee_is_shadowed_local_with_work(callee, caller_names, 0, work)" in (ROOT / "src/proof/check/alias_stability_integrated_helpers.elisa").read_text()
assert "proof_match_lowering_charge(sview_len(local_callee), work)" in (ROOT / "src/proof/check/alias_stability_integrated_helpers.elisa").read_text()
assert "proof_check_purity(block_body, functions, lemmas, report, name, names, work, 0, 1)" in blocks
assert "proof_check_lemma_purity(body, functions, lemmas, report, function_name, contract_caller_names, lemma_purity_work, 0)" in functions
assert "proof_check_purity_walk(body: darray[Ast::Stmt]&, functions: mutable ProofFunctionTable&, lemmas: ProofLemmaTable&, report: mutable ProofReport&, name: sview, caller_names: darray[sview]&" in purity
assert "def shadowable(value: i64) -> bool:" in fixture
assert "lemma shadowed_callable_fact(shadowable: fn(i64) -> bool, value: i64):" in fixture
assert "assert shadowable(value)" in fixture
assert 'finding["kind"] == "lemma-impure" and finding["name"] == "shadowed_callable_fact"' in runtime_regression

print("proof-block purity rejects callable names shadowed by the caller scope")
