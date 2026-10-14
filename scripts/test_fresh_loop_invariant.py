"""Fresh aggregate goals cannot enter or preserve loop invariants by structural equality."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

BINARY = qualified_test_binary.proof_test_binary(ROOT)
SOURCE = """def fresh_loop_invariant(value: i64, count: i64) -> void:
    requires count >= 0
    for index in 0..<count:
        invariant [value] == [value]
        pass
"""

with tempfile.TemporaryDirectory(prefix="fresh-loop-invariant-") as directory:
    path = Path(directory) / "fresh.elisa"
    path.write_text(SOURCE)
    for route in (("--json",), ("--function-json", "fresh_loop_invariant")):
        result = subprocess.run([BINARY, *route, str(path)], capture_output=True,
                                text=True, timeout=60)
        report = json.loads(result.stdout)
        assert result.returncode == 1 and report["status"] == "failed", (route, report)
        assert report["summary"]["semantic_errors"] == 0, (route, report["semantic_diagnostics"])
        assert report["replay"]["gaps"] == 0, (route, report["replay"])
        assert report["replay"]["certificates"] == report["replay"]["replayed"], (route, report["replay"])
        assert report["trust"]["trusted_assumptions"] == [], (route, report["trust"])
        kinds = {finding["kind"] for finding in report["findings"]
                 if finding["name"] == "fresh_loop_invariant"}
        assert {"invariant-unproven", "invariant-not-preserved"} <= kinds, (route, report["findings"])
        goals = [goal for goal in report["goals"]
                 if goal["name"] == "fresh_loop_invariant" and goal["rule"] == "goal"]
        assert len(goals) >= 2 and sum(not goal["proven"] for goal in goals) >= 2, (route, goals)
        assert not any(item["name"] == "fresh_loop_invariant" and item["verified"]
                       for item in report["declaration_details"]), (route, report["declaration_details"])

print("Fresh aggregate loop invariant: entry and preservation claims refused")
