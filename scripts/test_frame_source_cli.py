"""Source-bound frame CLI accounting keeps positive and rejected events distinct."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

BINARY = qualified_test_binary.proof_test_binary(ROOT)
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

# Frame certificate rows must remain attributable when separate modules reuse a function name.
# Each declaration has its own source offset and line, so both valid frame proofs should receive
# replay credit independently instead of being conflated into one simple-name bucket.
module_result = subprocess.run(
    [BINARY, "--json", str(ROOT / "test/repro" / "frame_same_name_modules.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
)
module_report = json.loads(module_result.stdout)
assert module_result.returncode == 0
assert module_report["admission_invariant_failure"] == ""
assert module_report["summary"]["obligations"] == 2
assert module_report["summary"]["obligations"] == module_report["summary"]["proven"]
assert module_report["trust"]["kernel_replayed_certificates"] == module_report["summary"]["proven"]
assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in module_report["goals"])
print("frame source CLI: same-named module owners retain separate replay credit")
