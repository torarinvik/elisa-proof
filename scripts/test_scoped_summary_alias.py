"""Call-result aliases retain source identity inside value-block initializers."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """def slot(flag: bool) -> usize:
    ensure result < 3
    return 1 if flag
    0

def checked(flag: bool, values: array[bool, 3]) -> bool:
    available: bool =
        index: usize = slot(flag)
        values[index]
    available
"""
for name, source, accepted in (
    ("scoped", BASE, True),
    ("nested", BASE.replace("        index: usize", "        inner: bool =\n            index: usize").replace("        values[index]", "            values[index]\n        inner"), True),
    ("rebound", BASE.replace("index: usize", "index: mutable usize").replace("        values[index]", "        index <- 3\n        values[index]"), False),
    ("other-index", BASE.replace("values[index]", "values[3]"), False),
    ("wider-result", BASE.replace("result < 3", "result <= 3").replace("return 1 if flag", "return 3 if flag"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert report["summary"]["semantic_errors"] == 0, (name, route, report)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
            else:
                assert report["findings"]
    print("scoped summary:", name, "accepted" if accepted else "refused")
