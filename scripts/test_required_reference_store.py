"""Required record references retain null exclusion through nullable field writes."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def run(name, function=None):
    mode = ["--function-json", function] if function else ["--json"]
    result = subprocess.run([BIN, *mode, str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, positive = run("required_reference_store_probe.elisa", "required_reference_store")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert any(d["verified"] and d["name"] == "required_reference_store"
           for d in positive["declaration_details"] if d["kind"] == "function")
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0
assert positive["replay"]["gaps"] == 0 and not positive["trust"]["trusted_assumptions"]
# This valid conditional claim still needs record post-state merging. Keep its
# current unsupported status explicit, rather than treating it as a false claim.
code, branch = run("required_reference_store_probe.elisa", "required_reference_branch_store")
assert code == 1 and branch["status"] == "failed", branch
assert branch["summary"]["semantic_errors"] == 0, branch["summary"]
assert any(f["kind"] == "ensure-unproven" and f["name"] == "required_reference_branch_store"
           for f in branch["findings"]), branch["findings"]
code, negative = run("required_reference_store_rejected.elisa")
assert code == 1 and negative["status"] == "failed", negative
assert negative["summary"]["semantic_errors"] == 0, negative["summary"]
for name in ("required_reference_missing_write", "required_reference_nullable_store",
             "required_reference_overwritten_store", "required_reference_shadow_store"):
    assert any(f["name"] == name and f["kind"] == "ensure-unproven"
               for f in negative["findings"]), negative["findings"]
assert negative["replay"]["gaps"] == 0 and not negative["trust"]["trusted_assumptions"]
print("required references replay; false stores rejected; conditional record-join gap remains explicit")
