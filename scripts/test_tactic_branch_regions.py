"""Exercise scratch-region children through nested split/cases and refusal."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
for fixture in ("branch", "nested_branch", "nested_cases", "branch_incomplete"):
    expected = 1 if fixture == "branch_incomplete" else 0
    run = subprocess.run([str(BINARY), "--tactics",
                          str(ROOT / "examples" / f"tactic_script_{fixture}.json"),
                          str(ROOT / "examples/verified.elisa")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected, (fixture, run.returncode, run.stderr)
    data = json.loads(run.stdout)
    if expected == 0:
        assert data["status"] == "proved", data
        assert data["tactic"]["branch_certificate_replayed"] is True, data
    else:
        assert data["status"] != "proved", data
        assert data["tactic"]["branch_certificate_replayed"] is False, data
print("tactic branch regions: nested split/cases replay and incomplete branch refusal passed")
