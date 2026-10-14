"""Conditional-call frame events retain every original success and failure."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

BINARY = qualified_test_binary.proof_test_binary(ROOT)
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

# A call returned directly by the caller is an evaluated source occurrence too. Its changes
# must flow through the same frame and preservation checks as calls in conditions.
return_callee = "def bump_value(value: mutable usize&) -> usize changes value:\n    value <- value + 1\n    return 1\n"
for name, frame, count, proven, finding in (
    ("return-allowed", "changes counter", 6, 6, None),
    ("return-outside", "changes other", 6, 5, "frame-write-outside"),
    ("return-preserved", "changes counter preserves other", 8, 8, None),
    ("return-overlap", "changes counter preserves counter", 8, 7, "frame-preserve-write"),
):
    source = "def run(counter: mutable usize&, other: usize) -> usize " + frame + ":\n    return bump_value(counter)\n" + return_callee
    with tempfile.TemporaryDirectory(prefix="frame-return-call-cli-") as directory:
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
    print("return call CLI:", name, count, "events", proven, "certificates")

# Calls in either arm of a scalar conditional expression are possible frame effects.
for name, frame, expression, proven, finding in (
    ("conditional-return-then", "changes counter", "bump_value(counter) if other == 0 else 0", True, None),
    ("conditional-return-else-outside", "changes other", "0 if other == 0 else bump_value(counter)", False, "frame-write-outside"),
):
    source = "def run(counter: mutable usize&, other: usize) -> usize " + frame + ":\n    return " + expression + "\n" + return_callee
    with tempfile.TemporaryDirectory(prefix="frame-conditional-return-cli-") as directory:
        path = Path(directory) / "control.elisa"
        path.write_text(source)
        for route in ("--json", "--summary-json"):
            result = subprocess.run([BINARY, route, str(path)], capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert report["admission_invariant_failure"] == "", (name, report)
            assert report["summary"]["obligations"] > 0, (name, report["summary"])
            if proven:
                assert result.returncode == 0 and report["status"] == "proved", (name, report)
                assert report["summary"]["proven"] == report["summary"]["obligations"], (name, report["summary"])
            else:
                assert result.returncode == 1 and report["status"] == "failed", (name, report)
                assert report["summary"]["proven"] < report["summary"]["obligations"], (name, report["summary"])
            assert report["trust"]["kernel_replayed_certificates"] == report["summary"]["proven"], name
            assert report["replay"]["gaps"] == 0, (name, report["replay"])
            if route == "--json" and finding:
                assert any(row["kind"] == finding for row in report["findings"]), (name, report["findings"])
    print("conditional return call CLI:", name, "complete" if proven else "refused")
