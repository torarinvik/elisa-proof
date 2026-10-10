"""Typed integer loop binders remain integers in float-bearing record frames."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/captured_search_assignment_invariant.elisa").read_text()
for name, source, accepted in (
    ("identity-result", BASE, True),
    ("nested-assignment", BASE.replace("    slot <- for index", "    if slot == 4:\n        slot <- for index").replace("        invariant slot", "            invariant slot").replace("        break index", "            break index"), True),
    ("zero-iterations", BASE.replace("0..<4", "0..<0"), True),
    ("wrong-entry", BASE.replace("|slot: usize = 4", "|slot: usize = 5"), False),
    ("wrong-preservation", BASE.replace("break index if", "break 5 if"), False),
    ("loose-invariant", BASE.replace("invariant slot <= 4", "invariant slot <= 5"), False),
    ("wide-range", BASE.replace("0..<4", "0..<5"), False),
    ("later-rebind", BASE.replace("    return if slot == 4", "    slot <- 5\n    return if slot == 4"), False),
    ("other-result", BASE.replace("|slot: usize = 4, store| -> slot:", "|found: usize = 4, store| -> found:").replace("invariant slot <= 4", "invariant found <= 4"), False),
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
                assert report["summary"]["proven"] == report["summary"]["obligations"] >= 8
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("block result bounds:", name, "accepted" if accepted else "refused")
