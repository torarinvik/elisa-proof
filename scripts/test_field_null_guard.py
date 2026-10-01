"""Null equality complements replay; wrong branches and stale fields fail."""

import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


status, positive = run("field_null_guard_probe.elisa")
assert status == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0
assert positive["replay"]["gaps"] == 0 and positive["trust"]["trusted_assumptions"] == []
assert all(d["verified"] for d in positive["declaration_details"] if d["kind"] == "function")

status, negative = run("field_null_guard_rejected.elisa")
assert status == 1 and negative["status"] == "failed", negative
assert negative["summary"]["semantic_errors"] == 0, negative["summary"]
for name in ("field_null_guard_wrong_branch", "field_null_guard_stale_write"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven" for f in negative["findings"]), negative["findings"]
assert negative["replay"]["gaps"] == 0 and negative["trust"]["trusted_assumptions"] == []

status, ordering = run("rejected_opaque_reference_ordering.elisa")
assert status == 1 and any(f["kind"] == "contract-proposition-type" for f in ordering["findings"])
status, scalar = run("field_null_guard_scalar_rejected.elisa")
assert status == 1 and scalar["status"] == "failed", scalar
assert scalar["summary"]["semantic_errors"] > 0 or any(f["kind"] == "contract-proposition-type" for f in scalar["findings"]), scalar
print("field null guards replay; wrong branches, stale writes, and pointer ordering rejected")
