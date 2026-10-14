"""A module-local function can type and replay target-sized range propositions."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]

BINARY = Path(qualified_test_binary.proof_test_binary(ROOT))
SOURCE = """module Foo:
    def valid_slice(start: usize, length: usize, data_count: usize) -> bool:
        requires start <= data_count and length <= data_count - start
        ensure start <= data_count and length <= data_count - start
        return true
"""

with tempfile.TemporaryDirectory(prefix="elisa-proof-module-proposition-") as directory:
    source = Path(directory) / "module-proposition.elisa"
    source.write_text(SOURCE, encoding="utf-8")
    run = subprocess.run([str(BINARY), "--json", str(source)], capture_output=True,
                         text=True, timeout=120)
    report = json.loads(run.stdout)
    assert run.returncode == 0 and report["status"] == "proved", (
        run.returncode, report.get("status"), report.get("findings"))
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["summary"]["obligations"] > 0, report["summary"]
    assert report["summary"]["unproven"] == 0, report["summary"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
    range_goal = next(goal for goal in report["goals"] if goal["name"] == "valid_slice")
    assert range_goal["proven"] and range_goal["replay_status"] == "replayed", range_goal

print("module-scoped usize range proposition: accepted with complete replay")
