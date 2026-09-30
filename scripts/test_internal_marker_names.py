"""Source declarations cannot capture private symbolic-state markers."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))

for filename, reserved_name in (
    ("rejected_entry_state_marker_collision.elisa", "__elisa_proof_entry_state"),
    ("rejected_scalar_reference_marker_collision.elisa", "__elisa_proof_scalar_reference_state"),
    ("rejected_field_place_marker_collision.elisa", "__elisa_field_place_1"),
    ("rejected_tuple_result_marker_collision.elisa", "__elisa_tuple_result"),
):
    result = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / filename)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1, (filename, result.returncode, result.stdout, result.stderr)
    report = json.loads(result.stdout)
    assert report["verification_state"] == "unsupported", report
    assert report["summary"]["semantic_errors"] == 0, report["summary"]
    assert report["summary"]["proven"] == 0, report["summary"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["findings"] == [{
        "kind": "proof-internal-name",
        "status": "unsupported",
        "line": 4 if "entry_state" in filename else 1,
        "name": reserved_name,
        "message": "source identifier collides with a proof-system internal name",
        "counterexample_found": False,
        "goal_id": None,
        "counterexample": [],
    }], (filename, report["findings"])
print("internal marker namespace: entry, scalar, tuple, and field-place collisions are refused")
