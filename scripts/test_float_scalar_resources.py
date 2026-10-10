"""IEEE float ownership classification must preserve actual borrow checks."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
CASES = (
    ("f32", "extern forward(value: f32) -> f32\ndef checked(value: f32) -> f32:\n    forward(value)\n", True),
    ("f64", "extern forward(value: f64) -> f64\ndef checked(value: f64) -> f64:\n    forward(value)\n", True),
    ("mutable-value", "extern forward(value: f32) -> f32\ndef checked(value: mutable f32) -> f32:\n    forward(value)\n", True),
    ("float-field", "struct Box:\n    value: f32\nextern forward(value: f32) -> f32\ndef checked(box: Box&) -> f32:\n    forward(box.value)\n", True),
    ("float-element", "struct Box:\n    values: f32[4]\nextern forward(value: f32) -> f32\ndef checked(box: Box&) -> f32:\n    forward(box.values[0])\n", True),
    ("field-borrow", "struct Box:\n    value: mutable f32\nextern touch(value: mutable f32&) -> void\ndef checked(box: mutable Box&) -> void:\n    touch(&box.value)\n", False),
    ("integer-field", "struct Box:\n    value: i64\nextern forward(value: i64) -> i64\ndef checked(box: Box&) -> i64:\n    forward(box.value)\n", True),
    ("overlapping-float-borrows", "def touch(left: mutable f32&, right: mutable f32&) -> void:\n    left <- 0.0\n    right <- 1.0\ndef checked(value: mutable f32&) -> void:\n    touch(value, value)\n", False),
    ("f32-reference", "extern touch(value: mutable f32&) -> void\ndef checked(value: mutable f32&) -> void:\n    touch(value)\n", False),
    ("f64-reference", "extern touch(value: mutable f64&) -> void\ndef checked(value: mutable f64&) -> void:\n    touch(value)\n", False),
    ("nan-reflexivity", "def checked(value: f32) -> bool:\n    ensure result\n    value == value\n", False),
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
                assert report["summary"]["proven"] == report["summary"]["obligations"]
                assert report["replay"]["gaps"] == 0
                assert all(d["verified"] for d in report["declaration_details"] if d["name"] == "checked")
            else:
                assert report["summary"]["unproven"] > 0
    print("float scalar resources:", name, "accepted" if accepted else "refused")
