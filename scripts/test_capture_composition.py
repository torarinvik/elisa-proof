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
    assert summary["proven"] == 73 and summary["failed"] == 1
    assert len(report["findings"]) == 1
    assert report["findings"][0]["goal_id"] == 73
    assert all(f["name"] == "capture_composition"
               and f["kind"] == "ensure-unproven" and f["status"] == "timeout"
               for f in report["findings"])
    print("known open capture composition reproduced: 73/74 replayed, one timeout")
else:
    assert result.returncode == 0 and report["status"] == "proved", report["findings"]
    assert summary["proven"] == 74 and summary["failed"] == 0
    assert not report["findings"]
    print("capture composition fully proved and independently replayed: 74/74")

# These controls call the two verified leaves directly. Rejection caused only by
# depending on the currently unverified composition would not test soundness.
for target in ("capture_composition_false_success", "capture_composition_false_touch",
               "capture_composition_false_invalid"):
    rejected = subprocess.run(
        [binary, "--function-json", target,
         str(ROOT / "examples/capture_composition_rejected.elisa")],
        capture_output=True, text=True, timeout=60)
    negative = json.loads(rejected.stdout)
    assert rejected.returncode == 1 and negative["status"] == "failed"
    assert negative["summary"]["semantic_errors"] == 0
    assert len(negative["findings"]) == 1
    finding = negative["findings"][0]
    assert finding["name"] == target and finding["kind"] == "ensure-unproven"
    assert negative["replay"]["gaps"] == 0
    assert negative["replay"]["certificates"] == negative["replay"]["replayed"] > 0
    assert not negative["trust"]["trusted_assumptions"]
    leaves = [d for d in negative["declaration_details"]
              if d.get("kind") == "function" and d.get("name") in
              ("capture_classify", "capture_stage")]
    assert len(leaves) == 2 and all(d["verified"] for d in leaves)
print("wrong success, touch denial, and invalid publication compositions rejected")
