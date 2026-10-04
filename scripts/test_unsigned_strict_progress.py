"""Positive steps must be bounded before unsigned order is lifted to integers."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def run(name, expected):
    process = subprocess.run([BIN, "--json", str(ROOT / "examples" / name)],
                             capture_output=True, text=True, timeout=60)
    report = json.loads(process.stdout)
    assert process.returncode == expected, report["findings"]
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    return report


positive = run("unsigned_strict_progress.elisa", 0)
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0
negative = run("rejected_unsigned_strict_progress.elisa", 1)
for target in ("zero_step_can_stall", "positive_step_can_wrap", "remainder_without_cap_can_wrap"):
    assert any(f["name"] == target and f["kind"] == "ensure-unproven"
               for f in negative["findings"]), target
    assert not any(d.get("name") == target and d.get("verified")
                   for d in negative["declaration_details"]), target
print("Bounded unsigned strict progress replays; stalled and wrapping controls reject")
