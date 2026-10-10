"""Typed integer loop binders remain integers in float-bearing record frames."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/captured_search_float_record.elisa").read_text()
FLOAT_PREFIX = "struct Store:\n    magnitude: f32\ndef checked(store: Store&) -> bool:\n    ensure result\n"
for name, source, accepted in (
    ("f32-record", BASE, True),
    ("f64-record", BASE.replace("magnitude: f32", "magnitude: f64"), True),
    ("wide-range", BASE.replace("0..<4", "0..<5"), False),
    ("wrong-initial", BASE.replace("slot: usize = 4", "slot: usize = 5"), False),
    ("wrong-break", BASE.replace("break index if", "break 5 if"), False),
    ("nan-reflexivity", FLOAT_PREFIX + "    store.magnitude == store.magnitude\n", False),
    ("nan-order", FLOAT_PREFIX + "    store.magnitude >= 0.0 or store.magnitude < 0.0\n", False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert not report["trust"]["trusted_assumptions"]
            assert report["summary"]["semantic_errors"] == 0
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"] == 8
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("mixed record search:", name, "accepted" if accepted else "refused")
