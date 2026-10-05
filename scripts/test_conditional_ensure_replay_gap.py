"""A conditional postcondition must never be admitted with a replay gap."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
SOURCE = ROOT / "test/repro/minimal_conditional_ensure_replay_gap.elisa"

run = subprocess.run([BINARY, "--json", str(SOURCE)], capture_output=True, text=True, timeout=20)
report = json.loads(run.stdout)
replay = report["replay"]
declaration = next(
    item for item in report["declaration_details"]
    if item.get("kind") == "function" and item.get("name") == "inner"
)

if replay["gaps"]:
    # Current behavior reproduces one lost certificate. Keep it explicitly refused;
    # a future fix must produce a fully replayed proof instead.
    assert report["status"] == "proved_with_replay_gaps", report
    assert run.returncode == 1, (run.returncode, report["status"])
    assert replay == {"certificates": 2, "replayed": 1, "gaps": 1}, replay
    assert report["verification_state"] != "proved", report["verification_state"]
    assert declaration["verified"] is False
    assert declaration["verification_reason"] == "replay-gap"
else:
    assert report["status"] == "proved", report["status"]
    assert run.returncode == 0, (run.returncode, report["status"])
    assert replay["certificates"] == replay["replayed"], replay
    assert declaration["verified"] is True, declaration

print("conditional ensure replay gap is refused, or fully replayed after a fix")
