"""Search-break bindings replay only in the original invariant scope."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/captured_search_invariant.elisa").read_text()
QUALIFIED = (ROOT / "examples/captured_search_qualified_constant.elisa").read_text()
for name, source, accepted in (
    ("valid", BASE, True),
    ("qualified", QUALIFIED, True),
    ("other-owner", "const module Other:\n    MAX: usize = 1\n" + QUALIFIED, True),
    ("qualified-wide", QUALIFIED.replace("MAX: usize = 4", "MAX: usize = 5"), False),
    ("wrong-owner", "const module Other:\n    MAX: usize = 5\n" + QUALIFIED.replace("slot: usize = Limits::MAX", "slot: usize = Other::MAX"), False),
    ("wide-range", BASE.replace("0..<4", "0..<5"), False),
    ("wide-initial", BASE.replace("slot: usize = 4", "slot: usize = 5"), False),
    ("wrong-invariant", BASE.replace("invariant slot <= 4", "invariant slot <= 3"), False),
    ("wrong-break-value", BASE.replace("break index if", "break 5 if"), False),
    ("stale-exit", BASE.replace("-> void:", "-> usize:\n    ensure result == 4").replace("    return if slot == 4", "    return 4 if slot == 4") + "    slot\n", False),
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
    print("search break replay:", name, "accepted" if accepted else "refused")
