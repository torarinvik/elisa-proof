"""Invariant-bearing for loops retain untouched guards, never mutated ones."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """struct Store:
    count: mutable usize
    flags: mutable bool[4]
def checked(store: mutable Store&) -> void:
    return if store.count >= 4
    hit: mutable usize = 4
    for index in 0..<4:
        invariant hit <= 4
        break if store.flags[index]
    slot: usize = store.count
    store.flags[slot] <- false
"""
for name, source, accepted in (
    ("read-only", BASE, True),
    ("zero-iterations", BASE.replace("0..<4:", "0..<0:"), True),
    ("changed-field", BASE.replace("        break if", "        store.count <- 4\n        break if"), False),
    ("wrong-entry", BASE.replace("store.count >= 4", "store.count > 4"), False),
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
    print("invariant for:", name, "accepted" if accepted else "refused")
