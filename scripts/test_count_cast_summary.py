"""A builtin integer cast has a primitive result type; an omitted bound stays refused."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/count_cast_summary.elisa"
run = subprocess.run([str(BINARY), "--json", str(SOURCE)],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 1, (run.returncode, run.stderr, run.stdout)
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0, report
assert report["replay"]["gaps"] == 0, report
assert report["replay"]["certificates"] == report["replay"]["replayed"], report
functions = {
    declaration["name"]: declaration
    for declaration in report["declaration_details"]
    if declaration.get("kind") == "function"
}
assert functions["terminated"]["verified"], functions["terminated"]
assert not functions["missing_upper_guard"]["verified"], functions["missing_upper_guard"]
assert any(
    goal["name"] == "missing_upper_guard" and not goal["proven"]
    for goal in report["goals"]
), report["goals"]
print("builtin count cast summary verifies; omitted upper-bound control remains refused")
