"""Region cleanup retains untouched outer scalars and refuses stale bounds."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """struct Store:
    flags: mutable bool[4]
def checked(store: mutable Store&, value: usize) -> void:
    return if value >= 4
    slot: usize = value
    region local_scope:
        local: usize = 0
        store.flags[0] <- false
    store.flags[slot] <- false
"""
for name, source, accepted in (
    ("untouched", BASE, True),
    ("declaration-only", BASE.replace("        store.flags[0] <- false\n", ""), True),
    ("wrong-entry", BASE.replace("value >= 4", "value > 4"), False),
    ("mutable-rebound", BASE.replace("slot: usize", "slot: mutable usize").replace("        store.flags[0] <- false", "        slot <- 4"), False),
    ("mutating-call", ("def change(value: mutable usize&) -> void:\n    value <- 4\n" + BASE).replace("slot: usize", "slot: mutable usize").replace("        store.flags[0] <- false", "        change(&slot)"), False),
    ("shadow-refused", BASE.replace("        store.flags[0] <- false", "        slot: usize = 4"), False),
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
    print("region outer facts:", name, "accepted" if accepted else "refused")
