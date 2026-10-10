"""Branch locals do not erase unchanged outer loop atoms."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "test/repro/branch_local_loop_atom.elisa").read_text()
for name, source, accepted in (
    ("both-arms-local", BASE, True),
    ("zero-iterations", BASE.replace("0..<4", "0..<0"), True),
    ("wrong-range", BASE.replace("0..<4", "0..<5"), False),
    ("rebound-outer", BASE.replace("    for index", "    slot: mutable usize = 0\n    for index").replace("store.flags[index]", "store.flags[slot]").replace("            local: usize = 0", "            local: usize = 0\n            slot <- 4"), False),
    ("shadowed-binder", BASE.replace("local: usize = 0", "index: usize = 4"), False),
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
    print("branch local loop atom:", name, "accepted" if accepted else "refused")
