"""Only source-witnessed unsigned place widening preserves comparison values."""
import json
import os
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__: raise SystemExit("run without Python -O")
for source, names, expected in (
    ("unsigned_widening.elisa", ("widening_u8_u16", "widening_u16_u32", "widening_zero_lower", "widening_order"), 0),
    ("rejected_unsigned_widening.elisa", ("rejected_narrowing", "rejected_signedness", "rejected_float_conversion", "rejected_widening_wrong_bound", "rejected_opaque_receiver"), 1),
):
    for name in names:
        run = subprocess.run([BIN, "--function-json", name, str(ROOT / "examples" / source)],
                             capture_output=True, text=True, timeout=60)
        report = json.loads(run.stdout)
        assert run.returncode == expected, (name, run.returncode, report.get("findings"), run.stderr)
        assert report["summary"]["semantic_errors"] == 0
        assert report["replay"]["gaps"] == 0
        assert report["replay"]["replayed"] == report["replay"]["certificates"]
        assert not report["trust"]["trusted_assumptions"]
        if expected == 0:
            assert report["status"] == "proved" and report["findings"] == []
        else:
            expected_kind = "contract-expression-unsupported" if name == "rejected_float_conversion" else "ensure-unproven"
            assert any(f["kind"] == expected_kind and f["name"] == name for f in report["findings"])
print("unsigned place widening replays; narrowing, signedness, float and wrong bounds reject")
