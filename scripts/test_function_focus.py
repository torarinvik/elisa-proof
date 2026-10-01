"""Focused function verification checks call closure and fail-closed selection."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/function_focus_probe.elisa"
REJECTED_SOURCE = ROOT / "examples/function_focus_rejected.elisa"
SCOPE_SOURCE = ROOT / "examples/function_focus_scope.elisa"


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

print("focused function verification: transitive callees proved, unrelated declarations skipped, selected false claims rejected")
