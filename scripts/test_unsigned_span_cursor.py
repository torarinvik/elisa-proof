"""Full-width unsigned span arithmetic and exact-premise rejection controls."""
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
run = subprocess.run([binary, "--json", str(root / "examples/unsigned_span_cursor.elisa")],
                     capture_output=True, text=True, timeout=30)
assert run.returncode == 1, run.stderr
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0
assert report["replay"]["replayed"] == report["replay"]["certificates"]
assert not report["trust"]["trusted_assumptions"]
assert {f["name"] for f in report["findings"]} == {
    "rejected_span_missing_step_bound", "rejected_span_missing_order", "rejected_span_other_step",
    "rejected_signed_span", "rejected_span_stale_cursor"}
for name in ("unsigned_prefix_cursor", "unsigned_suffix_cursor", "unsigned_byte_prefix", "unsigned_byte_suffix"):
    assert any(d.get("name") == name and d.get("verified") for d in report["declaration_details"])
print("Unsigned span cursors replay; missing bounds/order, unrelated step, signed and stale controls reject")
