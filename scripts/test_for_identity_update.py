"""For identity preservation replays from the exact source update; false bounds refuse."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """module M:
    const N: usize = 9
    def checked() -> usize:
        count: mutable usize = 0
        for i in 0..<N |count|:
            invariant count <= N
            count <- count
        count
"""
for name, source, accepted in (
    ("identity", BASE, True),
    ("header-result", BASE.replace("        count: mutable usize = 0\n        for i in 0..<N |count|:", "        for i in 0..<N |count: usize = 0| -> count:").replace("        count\n", ""), True),
    ("bound-result", BASE.replace("        count: mutable usize = 0\n        for i in 0..<N |count|:", "        result: usize =\n            for i in 0..<N |count: usize = 0| -> count:").replace("            invariant", "                invariant").replace("            count <-", "                count <-").replace("        count\n", "        result\n"), True),
    ("wrong-entry", BASE.replace("= 0", "= 10"), False),
    ("growing-update", BASE.replace("count <- count", "count <- count + 1"), False),
    ("wrong-update", BASE.replace("count <- count", "count <- 10"), False),
    ("wrong-invariant", BASE.replace("count <= N", "count > N"), False),
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
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"] == 3
                assert report["replay"]["gaps"] == 0
            else:
                assert report["findings"], (name, route, report["summary"])
    print("for identity:", name, "accepted" if accepted else "refused")
