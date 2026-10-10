"""Read-only for loops retain unrelated outer bounds; reachable mutations refuse."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/loop_readonly_outer_index.elisa").read_text()
for name, source, accepted in (
    ("readonly", BASE, True),
    ("wide-guard", BASE.replace("index >= 4", "index >= 5"), False),
    ("missing-guard", BASE.replace("    return if index >= 4\n", ""), False),
    ("index-rebind", BASE.replace("index: usize", "index: mutable usize").replace("    for other in 0..<4:", "    for other in 0..<4 |index|:\n        index <- 4"), False),
    ("index-alias", "extern touch(value: mutable usize&) -> void\n" + BASE.replace("index: usize", "index: mutable usize").replace("    for other in 0..<4:", "    for other in 0..<4 |index|:\n        touch(&index)"), False),
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
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"] >= 13
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("read-only outer index:", name, "accepted" if accepted else "refused")
