"""Fixed storage admits indexing even when scalar witness traversal is exhausted."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/late_fixed_array_index.elisa").read_text()
FIRST = BASE.replace("struct Store:\n", "struct Store:\n    flags: mutable bool[3]\n").replace("    flags: mutable bool[3]\ndef", "def")
CASES = (
    ("late", BASE, True),
    ("first", FIRST, True),
    ("qualified-extent", "const module Limits:\n    CAP: usize = 3\n" + BASE.replace("bool[3]", "bool[Limits::CAP]"), True),
    ("wide-bound", BASE.replace("index >= 3", "index >= 4"), False),
    ("missing-guard", BASE.replace("    return if index >= 3\n", ""), False),
    ("empty-storage", BASE.replace("bool[3]", "bool[0]"), False),
    ("shared-write", BASE.replace("store: mutable Store&", "store: Store&"), False),
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
    print("fixed index admission:", name, "accepted" if accepted else "refused")
