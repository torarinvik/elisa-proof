"""Track the scalar capture-summary gap without treating partial proof as success.

Default invocation requires complete proof. --expect-open explicitly checks the
known baseline while developing a bounded producer/replay search improvement.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--expect-open", action="store_true")
args = parser.parse_args()
if not __debug__:
    raise SystemExit("run without Python -O: regression assertions must remain enabled")
binary = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
result = subprocess.run(
    [binary, "--function-json", "capture_composition",
     str(ROOT / "examples/capture_composition_probe.elisa")],
    capture_output=True, text=True, timeout=60)
report = json.loads(result.stdout)
summary, replay = report["summary"], report["replay"]
assert summary["semantic_errors"] == 0
assert summary["semantic_diagnostics"] == 0
assert replay["gaps"] == 0
assert replay["certificates"] == replay["replayed"] == summary["proven"]
assert not report["trust"]["trusted_assumptions"]
assert summary["obligations"] == 74
if args.expect_open:
    assert result.returncode == 1 and report["status"] == "failed"
    assert summary["proven"] == 69 and summary["failed"] == 5
    assert len(report["findings"]) == 5
    assert all(f["name"] == "capture_composition"
               and f["kind"] == "ensure-unproven" and f["status"] == "timeout"
               for f in report["findings"])
    print("known open capture composition reproduced: 69/74 replayed, five timeouts")
else:
    assert result.returncode == 0 and report["status"] == "proved", report["findings"]
    assert summary["proven"] == 74 and summary["failed"] == 0
    assert not report["findings"]
    print("capture composition fully proved and independently replayed: 74/74")
