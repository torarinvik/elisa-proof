"""Unsigned nonzero discreteness, exact-term matching and negative controls."""
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
run = subprocess.run([binary, "--json", str(root / "examples/unsigned_nonzero_lower_bound.elisa")],
                     capture_output=True, text=True, timeout=30)
assert run.returncode == 1, run.stderr
report = json.loads(run.stdout)
# The pinned compiler also rejects this exact unrelated-parameter ensure.
# Do not permit any other semantic error or treat the refusal as a proof.
assert report["summary"]["semantic_errors"] == 1
assert [(d["kind_code"], d["name"]) for d in report["semantic_diagnostics"] if d["severity"] == 1] == [
    (311, "rejected_unsigned_other_term")]
assert [d["message"] for d in report["semantic_diagnostics"] if d["severity"] == 1] == [
    'ensure postcondition of "rejected_unsigned_other_term" could not be proven statically at this point']
assert report["replay"]["gaps"] == 0
assert report["replay"]["replayed"] == report["replay"]["certificates"]
assert not report["trust"]["trusted_assumptions"]
assert {f["name"] for f in report["findings"]} == {
    "rejected_signed_nonzero_positive", "rejected_unsigned_other_term",
    "rejected_unsigned_zero", "rejected_unsigned_stale"}
for name in ("unsigned_nonzero_usize", "unsigned_nonzero_u8", "unsigned_nonzero_branch",
             "unsigned_nonzero_reversed", "unsigned_nonzero_negated"):
    assert any(d.get("name") == name and d.get("verified") for d in report["declaration_details"])
print("Unsigned nonzero lower bounds replay; signed, unrelated, zero and stale controls reject")
