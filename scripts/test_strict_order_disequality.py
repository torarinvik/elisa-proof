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
    "equality_with_zero_excludes_u64_max",
}, positive["goals"]

negative = report("rejected_nonstrict_order_disequality", 1)
assert negative["status"] == "failed" and negative["verification_state"] == "disproved", negative
assert negative["summary"]["semantic_errors"] == 0 and negative["replay"]["gaps"] == 0, negative
assert any(finding["kind"] == "ensure-unproven" and finding["status"] == "disproved"
           and finding["counterexample_found"] for finding in negative["findings"]), negative

same_high_bit = report("rejected_u64_max_same_value_disequality", 1)
assert same_high_bit["status"] == "failed" and same_high_bit["verification_state"] in {"disproved", "unknown"}, same_high_bit
assert same_high_bit["summary"]["failed"] == 1 and same_high_bit["summary"]["semantic_errors"] == 0, same_high_bit
assert same_high_bit["replay"]["gaps"] == 0 and same_high_bit["trust"]["trusted_assumptions"] == [], same_high_bit
same_high_bit_finding = next(finding for finding in same_high_bit["findings"]
                             if finding["kind"] == "ensure-unproven")
assert same_high_bit_finding["counterexample_found"] == (same_high_bit["verification_state"] == "disproved"), same_high_bit

print("strict order/disequality: < and > replay; <= is refuted and identical u64-max is not certified")
