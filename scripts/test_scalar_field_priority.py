"""Scalar guards retain witnesses without raising aggregate traversal budgets."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/late_scalar_field_bounds.elisa").read_text()
FIRST = BASE.replace("struct Store:\n", "struct Store:\n    used: usize\n").replace("    used: usize\ndef", "def")
CASES = (
    ("scalar-last", BASE, True),
    ("scalar-first", FIRST, True),
    ("wide-count", BASE.replace("store.used <= 4", "store.used <= 5"), False),
    ("missing-capacity", BASE.replace("    requires store.used <= 4\n", ""), False),
    ("missing-index-guard", BASE.replace("    return false if index >= store.used\n", ""), False),
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
    print("scalar field priority:", name, "accepted" if accepted else "refused")
