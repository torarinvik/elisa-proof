"""Conditional-call frame events retain every original success and failure."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
callee = "def bump(value: mutable usize&) -> bool changes value:\n    value <- value + 1\n    return true\n"
for name, frame, count, proven, finding in (
    ("allowed", "changes counter", 6, 6, None),
    ("outside", "changes other", 6, 5, "frame-write-outside"),
    ("preserved", "changes counter preserves other", 8, 8, None),
    ("overlap", "changes counter preserves counter", 8, 7, "frame-preserve-write"),
):
    source = "def run(counter: mutable usize&, other: usize) -> usize " + frame + ":\n    return 1 if bump(counter)\n    return 0\n" + callee
    with tempfile.TemporaryDirectory(prefix="frame-call-cli-") as directory:
        path = Path(directory) / "control.elisa"
        path.write_text(source)
        for route in ("--json", "--summary-json"):
            result = subprocess.run([BINARY, route, str(path)], capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (1 if finding else 0), (name, report)
            assert report["admission_invariant_failure"] == "", name
            assert report["summary"]["obligations"] == count, (name, report["summary"])
            assert report["summary"]["proven"] == proven
            assert report["trust"]["kernel_replayed_certificates"] == proven
            if route == "--json" and finding:
                assert report["findings"][0]["kind"] == finding
                failed = report["goals"][report["findings"][0]["goal_id"]]
                assert not failed["proven"] and failed["certificate_id"] is None
    print("conditional call CLI:", name, count, "events", proven, "certificates")
