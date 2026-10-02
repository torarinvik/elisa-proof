"""Strict primitive order implies disequality and independently replays."""
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name: str, expected_exit: int) -> dict:
    run = subprocess.run([str(BINARY), "--json", str(ROOT / f"examples/{name}.elisa")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected_exit, (name, run.returncode, run.stderr, run.stdout)
    return json.loads(run.stdout)


positive = report("strict_order_disequality", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert positive["summary"]["semantic_errors"] == positive["summary"]["semantic_diagnostics"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] == positive["summary"]["proven"], positive
assert positive["replay"]["gaps"] == 0 and positive["trust"]["trusted_assumptions"] == [], positive
assert {goal["name"] for goal in positive["goals"]} == {
    "strict_less_excludes_equality", "strict_greater_excludes_reversed_equality",
    "equality_with_zero_excludes_u64_max", "equality_with_zero_excludes_parenthesized_u64_max",
    "later_strict_order_excludes_equality", "later_reversed_strict_order_excludes_equality",
}, positive["goals"]

negative = report("rejected_nonstrict_order_disequality", 1)
assert negative["status"] == "failed" and negative["verification_state"] == "disproved", negative
assert negative["summary"]["semantic_errors"] == 0 and negative["replay"]["gaps"] == 0, negative
assert any(finding["kind"] == "ensure-unproven" and finding["status"] == "disproved"
           and finding["counterexample_found"] for finding in negative["findings"]), negative

unrelated = report("rejected_unrelated_strict_order_disequality", 1)
assert unrelated["status"] == "failed", unrelated
assert unrelated["summary"]["semantic_errors"] == 0 and unrelated["replay"]["gaps"] == 0, unrelated
assert unrelated["trust"]["trusted_assumptions"] == [], unrelated
assert any(finding["kind"] == "ensure-unproven" and
           finding["name"] == "unrelated_order_does_not_exclude_equality"
           for finding in unrelated["findings"]), unrelated

same_high_bit = report("rejected_u64_max_same_value_disequality", 1)
assert same_high_bit["status"] == "failed" and same_high_bit["verification_state"] in {"disproved", "unknown"}, same_high_bit
assert same_high_bit["summary"]["failed"] == 1 and same_high_bit["summary"]["semantic_errors"] == 0, same_high_bit
assert same_high_bit["replay"]["gaps"] == 0 and same_high_bit["trust"]["trusted_assumptions"] == [], same_high_bit
same_high_bit_finding = next(finding for finding in same_high_bit["findings"]
                             if finding["kind"] == "ensure-unproven")
assert same_high_bit_finding["counterexample_found"] == (same_high_bit["verification_state"] == "disproved"), same_high_bit

unary_negative = report("rejected_u64_unary_negative_same_value", 1)
assert unary_negative["status"] == "failed" and unary_negative["verification_state"] in {"disproved", "unknown"}, unary_negative
assert unary_negative["summary"]["failed"] == 1 and unary_negative["summary"]["semantic_errors"] == 0, unary_negative
assert unary_negative["replay"]["gaps"] == 0 and unary_negative["trust"]["trusted_assumptions"] == [], unary_negative
unary_finding = next(finding for finding in unary_negative["findings"]
                     if finding["kind"] == "ensure-unproven")
assert unary_finding["counterexample_found"] == (unary_negative["verification_state"] == "disproved"), unary_negative

print("strict order/disequality: < and > replay; <= is refuted; literal, parenthesized, same-value and unary-negative boundaries checked")
