"""Reserved null identity closes typed field stores, not arbitrary references."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
run = subprocess.run([BIN, "--json", str(ROOT / "examples/null_store_identity_probe.elisa")],
                     capture_output=True, text=True, timeout=60)
report = json.loads(run.stdout)
assert run.returncode == 1 and report["status"] == "failed", report
assert report["summary"]["semantic_errors"] == 0
functions = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}
assert functions["clear_next"]["verified"], report["findings"]
for name in ("rejected_null_is_nonnull", "rejected_unwritten_next"):
    assert not functions[name]["verified"]
    assert any(f["name"] == name and f["kind"] == "ensure-unproven" for f in report["findings"])
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
print("typed null field store replays; nonnull and unwritten claims rejected")
