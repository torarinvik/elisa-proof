"""Lock down the OPEN extern boundary baseline; not feature admission."""
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
run = subprocess.run([binary, "--json", str(root / "examples/extern_recovery_boundary_gap.elisa")],
                     capture_output=True, text=True, timeout=30)
assert run.returncode == 1, run.stderr
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
assert report["replay"]["replayed"] == report["replay"]["certificates"]
assert not report["trust"]["trusted_assumptions"]
for name in ("rejected_unknown_extern_result_is_zero", "rejected_null_context_succeeds"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven" for f in report["findings"])
    assert not any(d.get("name") == name and d.get("verified") for d in report["declaration_details"])
# Keep unproved retention/resource properties distinct from the type/effect-row
# importer defects; resolving one must not silently admit the other.
expected_open = {
    "bounded_scalar_extern_result": {"effect-call-opaque", "ensure-unproven"},
    "nullable_context_after_call": {"effect-call-opaque", "borrow-call-opaque", "ensure-unproven"},
}
for name, kinds in expected_open.items():
    assert {f["kind"] for f in report["findings"] if f["name"] == name} == kinds
print("OPEN extern baseline reproduced; unknown return, nullable and retained-resource claims remain unadmitted")
