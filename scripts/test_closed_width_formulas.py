"""Closed width-independent OR formulas prove; width-dependent controls remain open."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("closed width checks must run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))

for fixture, expected in (("closed_goal_width_uniform", 0),
                          ("rejected_closed_goal_width_uniform", 1)):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (fixture + ".elisa"))],
                         capture_output=True, text=True, timeout=60)
    report = json.loads(run.stdout)
    assert run.returncode == expected, (fixture, report["findings"])
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["summary"]["obligations"] == 3, report["summary"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
    if expected == 0:
        assert report["status"] == "proved" and report["summary"]["proven"] == 3
    else:
        assert report["status"] == "failed" and report["summary"]["proven"] == 2
        assert len(report["findings"]) == 1 and report["findings"][0]["kind"] == "ensure-unproven"
print("closed width formulas: uniform truth replays; width-dependent false control refused")
