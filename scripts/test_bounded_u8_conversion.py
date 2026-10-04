"""Bounded signed-to-u8 conversion must preserve both machine boundaries."""
import json
import os
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for name, expected in (("bounded_row", 0), ("bounded_negated_peer", 0), ("rejected_nonstrict_peer", 1), ("rejected_row_bound", 1),
                       ("rejected_source_overflow", 1), ("rejected_destination_overflow", 1),
                       ("rejected_negative_conversion", 1)):
    result = subprocess.run([BIN, "--function-json", name,
                             str(ROOT / "examples/bounded_u8_conversion.elisa")],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == expected, (name, result.returncode, report.get("findings"), result.stderr)
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    if expected == 0:
        assert report["status"] == "proved" and not report["findings"]
    else:
        assert any(f["kind"] == "ensure-unproven" for f in report["findings"])
print("bounded u8 conversion replays; false bounds, source/destination overflow and negative values reject")
