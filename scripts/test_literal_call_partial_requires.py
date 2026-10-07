"""A refused call replays individually established literal preconditions."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """def checked(value: i64, weight: i64) -> i64:
    requires value >= 0
    requires weight >= 0
    ensure result == value
    return value
def refusal(value: i64) -> i64:
    return checked(value, 0)
"""
for name, source in (
    ("partial-requires", BASE),
    ("negative-literal", BASE.replace("checked(value, 0)", "checked(value, -1)").replace("requires weight >= 0", "requires weight >= -1")),
    ("declaration-call", BASE.replace("    return checked(value, 0)", "    output: i64 = checked(value, 0)\n    return output")),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["refusal"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            assert run.returncode == 1, (name, report)
            assert report["summary"]["semantic_errors"] == 0
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert report["replay"]["certificates"] == report["replay"]["replayed"]
            assert any(f["kind"] == "call-requires-unproven" for f in report["findings"])
            assert not report["trust"]["trusted_assumptions"]
    print("literal call preconditions:", name, "refused with complete replay")
