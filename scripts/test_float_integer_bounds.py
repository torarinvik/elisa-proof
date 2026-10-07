"""Unrelated float fields must not suppress witnessed integer bounds."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/record_short_circuit_index_control.elisa").read_text()
FLOAT = BASE.replace("    live: bool", "    value: f32\n    live: bool")
CASES = (
    ("integer-only", BASE, True),
    ("float-before", FLOAT, True),
    ("float-after", BASE.replace("    live: bool", "    live: bool\n    value: f32"), True),
    ("unsafe-upper", FLOAT.replace("index >= 4", "index > 4"), False),
    ("missing-guard", FLOAT.replace("index >= 4 or ", ""), False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["obligations"] >= 3
                assert report["summary"]["proven"] == report["summary"]["obligations"]
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("float integer bounds:", name, "accepted" if accepted else "refused")
