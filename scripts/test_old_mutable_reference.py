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
