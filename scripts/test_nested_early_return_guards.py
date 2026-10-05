"""Nested early-return guards survive if and loop bodies; unguarded indexing stays open."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/nested_early_return_guards.elisa"

run = subprocess.run([str(BINARY), "--json", str(SOURCE)], capture_output=True, text=True, timeout=120)
assert run.returncode == 1, (run.returncode, run.stderr)
data = json.loads(run.stdout)
assert data["summary"]["semantic_errors"] == 0, data["summary"]
assert data["replay"]["gaps"] == 0, data["replay"]
assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data["replay"]
functions = {d["name"]: d for d in data["declaration_details"] if d.get("kind") == "function"}
for name in ("nested_if_guard", "guard_nested_in_if", "nested_loop_guard"):
    assert functions[name]["verified"], (name, functions[name])
assert not functions["nested_loop_guard_false_control"]["verified"]
assert any(f["name"] == "nested_loop_guard_false_control" and f["kind"] == "index-upper-unproven"
           for f in data["findings"]), data["findings"]
print("nested early-return guards: if and loop positions prove; unguarded control stays open")
