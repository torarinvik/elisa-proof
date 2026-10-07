"""Source-bound frame CLI accounting keeps positive and rejected events distinct."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
for name, count, proven, finding in (
    ("allowed", 3, 3, None),
    ("outside_rejected", 3, 2, "frame-write-outside"),
    ("preserve_rejected", 5, 4, "frame-preserve-write"),
):
    for route in ("--json", "--summary-json"):
        result = subprocess.run([BINARY, route, str(ROOT / "test/repro" / ("frame_accounting_" + name + ".elisa"))], capture_output=True, text=True, timeout=60)
        report = json.loads(result.stdout)
        assert result.returncode == (0 if finding is None else 1), (name, route)
        assert report["admission_invariant_failure"] == "", (name, route)
        summary = report["summary"]
        assert (summary["obligations"], summary["proven"], summary["finding_count"]) == (count, proven, 0 if finding is None else 1)
        assert report["trust"]["kernel_replayed_certificates"] == proven
        if route == "--json":
            goals = report["goals"]
            assert len(goals) == count
            assert all(goal["replay_status"] == "replayed" for goal in goals if goal["proven"])
            if finding:
                diagnostic = report["findings"][0]
                assert diagnostic["kind"] == finding
                goal = goals[diagnostic["goal_id"]]
                assert not goal["proven"] and goal["rule"] in ("frame-allow", "frame-preserve")
                assert goal["certificate_id"] is None
    print("frame source CLI:", name, "retains", count, "events and", proven, "certificates")
