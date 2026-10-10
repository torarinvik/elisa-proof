"""An exact scalar copy/restore preserves a for invariant; changed copies refuse."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """def checked(start: usize, stop: usize) -> usize:
    requires start <= stop
    cursor: mutable usize = start
    for index in 0..<9 |cursor|:
        invariant cursor <= stop
        saved: usize = cursor
        cursor <- saved
    cursor
"""
for name, source, accepted in (
    ("copy-restore", BASE, True),
    ("wrong-entry", BASE.replace("    requires start <= stop\n", ""), False),
    ("different-copy", BASE.replace("saved: usize = cursor", "saved: usize = stop + 1"), False),
    ("changed-update", BASE.replace("cursor <- saved", "cursor <- saved + 1"), False),
    ("mutable-copy", BASE.replace("saved: usize", "saved: mutable usize").replace("        cursor <- saved", "        saved <- stop + 1\n        cursor <- saved"), False),
    ("late-postcondition", BASE.replace("    requires", "    ensure result <= stop\n    requires").replace("    cursor\n", "    cursor <- stop + 1\n    cursor\n"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert report["summary"]["semantic_errors"] == 0
            assert not report["trust"]["trusted_assumptions"]
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"] == 3
                assert report["replay"]["gaps"] == 0
            else:
                assert report["findings"], (name, route, report["summary"])
    print("for alias:", name, "accepted" if accepted else "refused")
