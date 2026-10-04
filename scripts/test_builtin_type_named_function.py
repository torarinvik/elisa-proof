"""A bare call named like a builtin scalar type is a conversion and must not use a contract."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples/rejected_builtin_type_named_function.elisa")],
                     capture_output=True, text=True, timeout=120)
assert run.returncode == 1, (run.returncode, run.stderr[-2000:], run.stdout[-2000:])
report = json.loads(run.stdout)
assert report["status"] == "failed", report["status"]
assert report["replay"]["gaps"] == 0
details = {d["name"]: d for d in report["declaration_details"]}
for name in ("rejected_cast_is_not_the_shadowing_function", "rejected_isize_cast_through_local"):
    assert not details[name]["verified"], details[name]
    assert any(f["name"] == name for f in report["findings"]), (name, report["findings"])
# The shadowing functions themselves are still checked; only their bare-name calls are casts.
assert details["i64"]["verified"] and details["isize"]["verified"], (details["i64"], details["isize"])
print("bare builtin-type calls are conversions, never the shadowing function's contract")
