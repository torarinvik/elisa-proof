"""Private declaration frames export immutable scalar facts and expire locals."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """def checked(seed: usize) -> usize:
    ensure result == seed
    output: usize =
        local: usize = seed
        local
    return output
"""
CAPTURE = """def checked() -> usize:
    ensure result == 1
    count: mutable usize = 0
    output: usize = |count|
        local: usize = 1
        count <- local
        local
    return count
"""
for name, source, accepted in (
    ("immutable-result", BASE, True),
    ("expired-name-reuse", (ROOT / "test/repro/value_block_local_reuse.elisa").read_text(), True),
    ("outer-capture", CAPTURE, True),
    ("capture-wrong-result", CAPTURE.replace("local: usize = 1", "local: usize = 2"), False),
    ("capture-later-write", CAPTURE.replace("    return count", "    count <- 2\n    return count"), False),
    ("wrong-result", BASE.replace("local: usize = seed", "local: usize = 0"), False),
    ("inner-mutation", BASE.replace("local: usize = seed", "local: mutable usize = seed\n        local <- 0"), False),
    ("result-rebound", BASE.replace("output: usize", "output: mutable usize").replace("    return output", "    output <- 0\n    return output"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            assert report["summary"]["semantic_errors"] == 0, (name, route, report)
            assert run.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
            else:
                assert report["findings"]
    print("private value declaration:", name, "accepted" if accepted else "refused")
