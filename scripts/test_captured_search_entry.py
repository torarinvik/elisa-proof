"""An unrelated record capture does not erase fresh scalar entry evidence."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "test/repro/read_only_search_field_bound.elisa").read_text()
for name, source, accepted in (
    ("read-only-search", BASE, True),
    ("zero-iterations", BASE.replace("0..<4", "0..<0"), True),
    ("wrong-initializer", BASE.replace("hit: usize = 4", "hit: usize = 5"), False),
    ("wrong-preservation", BASE.replace("break index if store.flags[index]", "hit <- 5"), False),
    ("changed-record", BASE.replace("    slot: usize", "    store.count <- 4\n    slot: usize"), False),
    ("wrong-entry-bound", BASE.replace("store.count >= 4", "store.count > 4"), False),
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
    print("captured search:", name, "accepted" if accepted else "refused")
