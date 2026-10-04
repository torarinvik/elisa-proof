"""Direct local field writes preserve other roots; alias/shadow claims fail."""

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


status, positive = run("local_record_field_probe.elisa")
assert status == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["semantic_errors"] == 0
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0
assert positive["replay"]["gaps"] == 0 and positive["trust"]["trusted_assumptions"] == []
assert all(d["verified"] for d in positive["declaration_details"] if d["kind"] == "function")

status, negative = run("local_record_field_rejected.elisa")
assert status == 1 and negative["status"] == "failed", negative
assert negative["summary"]["semantic_errors"] == 0, negative["summary"]
for name in ("local_record_field_reject_stale_value", "local_record_field_reject_reference_alias",
             "local_record_field_reject_shadow"):
    assert any(f["kind"] == "ensure-unproven" and f["name"] == name for f in negative["findings"]), negative["findings"]
assert negative["replay"]["gaps"] == 0 and negative["trust"]["trusted_assumptions"] == []
print("local record fields preserve other roots; stale, reference-alias, and shadow claims rejected")
