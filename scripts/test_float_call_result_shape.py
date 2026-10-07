"""Float call receiver admission preserves IEEE and source dispatch refusal."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = "extern forward(value: f32) -> f32\ndef checked(value: f32) -> bool:\n    forward(value) < 1.0\n"
CASES = (
    ("extern-f32", BASE, True),
    ("extern-f64", BASE.replace("f32", "f64"), True),
    ("source-f32", BASE.replace("extern forward(value: f32) -> f32", "def forward(value: f32) -> f32:\n    value"), True),
    ("nan-result", BASE.replace("    forward(value) < 1.0", "    ensures result\n    forward(value) == forward(value)"), False),
    ("overridden-equality", "protocol Eq:\n    def __eq__(self: Self, other: Self) -> bool\nimpl Eq for f32:\n    def __eq__(self: f32, other: f32) -> bool:\n        false\n" + BASE.replace("forward(value) < 1.0", "forward(value) == 1.0"), False),
    ("record-result", "struct Box:\n    value: f32\nextern forward(value: f32) -> Box\ndef checked(value: f32) -> bool:\n    forward(value) == forward(value)\n", False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"], report["findings"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("float call result:", name, "accepted" if accepted else "refused")
