"""Focused function verification checks call closure and fail-closed selection."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from qualified_test_binary import proof_test_binary

ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)
SOURCE = ROOT / "examples/function_focus_probe.elisa"
REJECTED_SOURCE = ROOT / "examples/function_focus_rejected.elisa"
SCOPE_SOURCE = ROOT / "examples/function_focus_scope.elisa"
DUPLICATE_MODULE_SOURCE = ROOT / "examples/function_focus_duplicate_module_scope.elisa"
MUTUAL_RECURSION_SOURCE = ROOT / "examples/mutual_recursive_pure_contract_call.elisa"


def run(source: Path, *arguments: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run(
        [str(BINARY), *arguments, str(source)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    report = json.loads(result.stdout)
    return result, report


positive_run, positive = run(SOURCE, "--function-json", "function_focus_caller")
assert positive_run.returncode == 0, (positive_run.returncode, positive_run.stderr)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert positive["focus"]["kind"] == "function-and-transitive-callees", positive.get("focus")
assert positive["focus"]["name"] == "function_focus_caller", positive.get("focus")
assert positive["focus"]["unrequested_proposition_findings"] == [], positive["focus"]
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert positive["summary"]["obligations"] == positive["summary"]["proven"] > 0
assert positive["summary"]["failed"] == 0
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0
assert positive["replay"]["gaps"] == 0
assert positive["trust"]["trusted_assumptions"] == []
functions = {
    item["name"]: item
    for item in positive["declaration_details"]
    if item.get("kind") == "function"
}
assert functions["function_focus_leaf"]["verified"], functions
assert functions["function_focus_caller"]["verified"], functions
assert not functions["function_focus_unrequested_valid"]["verified"], functions
assert functions["function_focus_unrequested_valid"]["verification_reason"] == "not-requested"
assert all(goal["name"] != "function_focus_unrequested_valid" for goal in positive["goals"])

# Focusing on an external caller reaches the full recursive SCC. Both members must be
# scheduled so the cycle cannot be treated as an unverified dependency.
mutual_run, mutual = run(
    MUTUAL_RECURSION_SOURCE, "--function-json", "uses_mutual_recursive_pure_contract_call"
)
assert mutual_run.returncode == 0 and mutual["status"] == "proved", mutual
assert mutual["focus"]["kind"] == "function-and-transitive-callees", mutual.get("focus")
mutual_functions = {
    item["name"]: item for item in mutual["declaration_details"] if item.get("kind") == "function"
}
for name in (
    "uses_mutual_recursive_pure_contract_call",
    "pure_even",
    "pure_odd",
):
    assert mutual_functions[name]["verified"], mutual_functions
assert mutual["summary"]["failed"] == 0 and mutual["replay"]["gaps"] == 0, mutual

# Selecting one SCC member directly must include its partner but leave the unrelated caller
# outside the focused dependency closure.
member_run, member = run(MUTUAL_RECURSION_SOURCE, "--function-json", "pure_even")
assert member_run.returncode == 0 and member["status"] == "proved", member
member_functions = {
    item["name"]: item for item in member["declaration_details"] if item.get("kind") == "function"
}
assert member_functions["pure_even"]["verified"], member_functions
assert member_functions["pure_odd"]["verified"], member_functions
assert not member_functions["uses_mutual_recursive_pure_contract_call"]["verified"], member_functions
assert (
    member_functions["uses_mutual_recursive_pure_contract_call"]["verification_reason"]
    == "not-requested"
), member_functions

negative_run, negative = run(REJECTED_SOURCE, "--function-json", "function_focus_requested_false")
assert negative_run.returncode == 1, (negative_run.returncode, negative_run.stderr)
assert negative["status"] == "failed", negative
assert negative["summary"]["semantic_errors"] == 1, negative["summary"]
assert any(
    finding["kind"] == "ensure-unproven"
    and finding["name"] == "function_focus_requested_false"
    for finding in negative["findings"]
), negative["findings"]
assert negative["replay"]["gaps"] == 0
assert negative["replay"]["certificates"] == negative["replay"]["replayed"]

unknown_run, unknown = run(SOURCE, "--function-json", "function_focus_missing")
assert unknown_run.returncode == 1, (unknown_run.returncode, unknown_run.stderr)
assert unknown["status"] == "failed", unknown
assert any(
    finding["kind"] == "function-focus-not-found"
    and finding["name"] == "function_focus_missing"
    for finding in unknown["findings"]
), unknown["findings"]

full_run = subprocess.run(
    [str(BINARY), "--json", str(SOURCE)],
    capture_output=True,
    text=True,
    timeout=60,
    check=False,
)
full = json.loads(full_run.stdout)
assert full_run.returncode == 0 and full["status"] == "proved", full
full_functions = {
    item["name"]: item
    for item in full["declaration_details"]
    if item.get("kind") == "function"
}
assert full_functions["function_focus_unrequested_valid"]["verified"], full_functions

# The fixture also contains a supported postcondition inside an unrelated module. Its bare-name
# source inventory is intentionally refused, but that must not veto the selected top-level proof.
scoped_run, scoped = run(SCOPE_SOURCE, "--function-json", "function_focus_scope_valid")
assert scoped_run.returncode == 0 and scoped["status"] == "proved", scoped
excluded = scoped["focus"]["unrequested_proposition_findings"]
assert len(excluded) == 1 and excluded[0]["kind"] == "contract-proposition-type", excluded
assert excluded[0]["name"] == "function_focus_scope_unsupported", excluded
assert scoped["findings"] == [] and scoped["summary"]["failed"] == 0, scoped
assert scoped["summary"]["semantic_errors"] == 0, scoped["summary"]

dependent_run, dependent = run(SCOPE_SOURCE, "--function-json", "function_focus_scope_dependent")
assert dependent_run.returncode == 1 and dependent["status"] == "failed", dependent
assert dependent["focus"]["unrequested_proposition_findings"] == [], dependent["focus"]
assert any(f["kind"] == "contract-proposition-type" and
           f["name"] == "function_focus_scope_unsupported" for f in dependent["findings"]), dependent

scope_full_run, scope_full = run(SCOPE_SOURCE, "--json")
assert scope_full_run.returncode == 1 and scope_full["status"] == "failed", scope_full
assert "focus" not in scope_full, scope_full
assert any(f["kind"] == "contract-proposition-type" for f in scope_full["findings"]), scope_full

# Same-leaf calls in nested modules must be filtered by declaration identity. Both functions have
# the innermost owner `Inner`, so the declaration position disambiguates the unrelated unsupported
# proposition from the selected target. Raw call spellings contain only `shared`.
duplicate_run, duplicate = run(
    DUPLICATE_MODULE_SOURCE, "--function-json", "focus_duplicate_module_caller"
)
assert duplicate_run.returncode == 0 and duplicate["status"] == "proved", duplicate
duplicate_excluded = duplicate["focus"]["unrequested_proposition_findings"]
assert len(duplicate_excluded) == 1, duplicate["focus"]
assert duplicate_excluded[0]["kind"] == "contract-proposition-type", duplicate_excluded
assert duplicate_excluded[0]["name"] == "shared", duplicate_excluded
assert duplicate["findings"] == [] and duplicate["summary"]["failed"] == 0, duplicate
duplicate_functions = {
    item["name"]: []
    for item in duplicate["declaration_details"]
    if item.get("kind") == "function"
}
for item in duplicate["declaration_details"]:
    if item.get("kind") == "function":
        duplicate_functions[item["name"]].append(item)
assert duplicate_functions["focus_duplicate_module_caller"][0]["verified"], duplicate_functions
assert len(duplicate_functions["shared"]) == 2, duplicate_functions
assert sorted(item["verified"] for item in duplicate_functions["shared"]) == [False, True], duplicate_functions

# A canonical module path selects the requested declaration even when another module has a
# same-leaf function with an unsupported contract. The unqualified leaf remains ambiguous.
qualified_run, qualified = run(
    DUPLICATE_MODULE_SOURCE,
    "--function-json",
    "FocusDuplicateSelected::Inner::shared",
)
assert qualified_run.returncode == 0 and qualified["status"] == "proved", qualified
assert qualified["focus"]["name"] == "FocusDuplicateSelected::Inner::shared", qualified["focus"]
qualified_shared = [
    item for item in qualified["declaration_details"]
    if item.get("kind") == "function" and item["name"] == "shared"
]
assert len(qualified_shared) == 2, qualified["declaration_details"]
assert sum(item["verified"] for item in qualified_shared) == 1, qualified_shared
assert qualified["findings"] == [] and qualified["summary"]["failed"] == 0, qualified
qualified_excluded = qualified["focus"]["unrequested_proposition_findings"]
assert len(qualified_excluded) == 1, qualified["focus"]
assert qualified_excluded[0]["kind"] == "contract-proposition-type", qualified_excluded
assert qualified_excluded[0]["name"] == "shared", qualified_excluded

ambiguous_run, ambiguous = run(DUPLICATE_MODULE_SOURCE, "--function-json", "shared")
assert ambiguous_run.returncode == 1 and ambiguous["status"] == "failed", ambiguous
assert any(finding["kind"] == "function-focus-not-found" for finding in ambiguous["findings"]), ambiguous

print("focused function verification: transitive callees proved, unrelated declarations skipped, selected false claims rejected")
