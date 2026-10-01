#!/usr/bin/env python3
"""JSON source positions across includes, and per-function status that counts findings."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
source = ROOT / "examples/rejected_source_map_include.elisa"
run = subprocess.run([str(BINARY), "--json", str(source)], capture_output=True, text=True, timeout=120)
assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
files = report["files"]
assert [Path(f).name for f in files] == ["rejected_source_map_include.elisa",
                                         "rejected_effectful_numeric_cast_contract.elisa"], files
lines = {i: path.read_text().splitlines() for i, path in enumerate(map(Path, files))}
for entry in report["findings"] + report["goals"]:
    assert entry["file_line"] <= len(lines[entry["file"]]), entry
by_kind = {(f["name"], f["kind"]): f for f in report["findings"]}
included = by_kind[("rejected_effectful_status_cast", "contract-call-unsupported")]
assert (included["file"], included["file_line"]) == (1, 8), included
assert "ensure result ==" in lines[1][7], lines[1][7]
root = by_kind[("only_finding", "contract-call-unsupported")]
assert root["goal_id"] is None and root["file"] == 0, root
assert "requires effectful_status" in lines[0][root["file_line"] - 1], root
functions = {f["name"]: f for f in report["functions"]}
# Every goal of `only_finding` is proven, yet its unbound finding keeps it unproved.
assert functions["only_finding"]["open_goals"] == 0 and functions["only_finding"]["findings"] == 1, functions
assert not functions["only_finding"]["proved"], functions
assert functions["kept"]["proved"] and functions["effectful_status"]["proved"], functions
assert not functions["rejected_effectful_status_cast"]["proved"], functions
print("source map: ok")
