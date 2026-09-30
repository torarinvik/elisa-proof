"""Mutable aggregate references do not collapse `old` to the current pointee."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
result = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/rejected_old_mutable_reference.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
)
assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
report = json.loads(result.stdout)
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
assert not any(
    declaration["name"] == "changed_field_is_not_its_entry_value" and declaration["verified"]
    for declaration in report["declaration_details"]
), report["declaration_details"]
assert any(
    finding["name"] == "changed_field_is_not_its_entry_value"
    and finding["kind"] in ("contract-proposition-type", "ensure-unproven")
    for finding in report["findings"]
), report["findings"]
print("mutable aggregate old-state: changed pointee is not identified with its entry value")

# An owned mutable aggregate is a separate case from `Cell&`: its binding also stays stable
# across field writes, but `old(cell.value)` must not collapse to the current field.
owned_result = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/rejected_old_mutable_value_aggregate.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
)
assert owned_result.returncode == 1, (owned_result.returncode, owned_result.stdout, owned_result.stderr)
owned_report = json.loads(owned_result.stdout)
assert owned_report["summary"]["semantic_errors"] == 0, owned_report["summary"]
assert owned_report["replay"]["gaps"] == 0, owned_report["replay"]
assert owned_report["replay"]["certificates"] == owned_report["replay"]["replayed"], owned_report["replay"]
assert not any(
    certificate["name"] == "changed_owned_field_is_not_its_entry_value" and certificate["line"] == 7
    for certificate in owned_report["certificates"]
), owned_report["certificates"]
assert not any(
    declaration["name"] == "changed_owned_field_is_not_its_entry_value" and declaration["verified"]
    for declaration in owned_report["declaration_details"]
), owned_report["declaration_details"]
assert any(
    finding["name"] == "changed_owned_field_is_not_its_entry_value"
    and finding["kind"] == "ensure-unproven"
    and finding["line"] == 7
    and finding.get("refusal_gate") == "no-rule"
    and not finding["counterexample_found"]
    for finding in owned_report["findings"]
), owned_report["findings"]
print("mutable owned aggregate old-state: post-write field was not replayed as its entry value")
