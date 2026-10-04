"""A write through a mutable reference local must invalidate what the checker knew of its referent."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/rejected_reference_local_write.elisa")],
                     capture_output=True, text=True, timeout=120)
assert run.returncode == 1, (run.returncode, run.stderr[-2000:], run.stdout[-2000:])
report = json.loads(run.stdout)
assert report["status"] == "failed", report["status"]
details = {d["name"]: d for d in report["declaration_details"]}
for name in ("rejected_write_through_reference_local", "rejected_stale_fact_after_reference_write", "rejected_branch_write_through_reference"):
    assert not details[name]["verified"], details[name]
print("reference-local writes havoc the referent's symbolic value")
