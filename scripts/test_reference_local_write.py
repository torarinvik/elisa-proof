"""A write through a mutable reference local must invalidate what the checker knew of its referent."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("reference-local write checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/rejected_reference_local_write.elisa")],
                     capture_output=True, text=True, timeout=120)
assert run.returncode == 1, (run.returncode, run.stderr[-2000:], run.stdout[-2000:])
report = json.loads(run.stdout)
assert report["status"] == "failed", report["status"]
assert report["verification_state"] != "proved", report["verification_state"]
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
details = {d["name"]: d for d in report["declaration_details"]}
expected_refusals = {
    "rejected_write_through_reference_local": {"ensure-unproven"},
    "rejected_stale_fact_after_reference_write": {"proof-step-unproven", "proof-unproven"},
    "rejected_branch_write_through_reference": {"ensure-unproven"},
}
for name, expected in expected_refusals.items():
    assert not details[name]["verified"], details[name]
    actual = {finding["kind"] for finding in report["findings"] if finding["name"] == name}
    assert actual == expected, (name, actual, expected)

control = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/reference_local_read_control.elisa")],
    capture_output=True, text=True, timeout=120)
assert control.returncode == 0, (control.returncode, control.stdout, control.stderr)
positive = json.loads(control.stdout)
assert positive["status"] == "proved", positive["findings"]
assert positive["summary"]["semantic_errors"] == 0, positive["semantic_diagnostics"]
assert positive["summary"]["obligations"] > 0, positive["summary"]
assert positive["replay"]["gaps"] == 0, positive["replay"]
assert positive["replay"]["certificates"] == positive["replay"]["replayed"], positive["replay"]
print("reference-local writes havoc the referent's symbolic value")
