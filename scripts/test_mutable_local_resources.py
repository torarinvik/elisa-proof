"""Mutable local declarations and their loop captures retain write capability."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
run = subprocess.run(
    [BINARY, "--json", str(ROOT / "examples/mutable_local_resources.elisa")],
    capture_output=True, text=True, timeout=60)
report = json.loads(run.stdout)
assert run.returncode == 0 and report["status"] == "proved", report["findings"]
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0
assert report["replay"]["certificates"] == report["replay"]["replayed"]
functions = {item["name"]: item for item in report["functions"]}
assert {"direct_write", "captured_write"} <= functions.keys()
assert all(functions[name]["proved"] and functions[name]["findings"] == 0
           for name in ("direct_write", "captured_write")), functions
print("mutable locals and captured loop accumulators prove and replay")
