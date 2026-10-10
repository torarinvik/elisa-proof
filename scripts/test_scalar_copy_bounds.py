"""Immutable copied bounds survive field mutation; current-field claims do not."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "test/repro/scalar_field_snapshot_bound.elisa").read_text()
CASES = (
    ("immutable-copy", BASE, True),
    ("local-guard", (ROOT / "test/repro/scalar_field_snapshot_local_guard.elisa").read_text(), True),
    ("parameter", (ROOT / "test/repro/scalar_field_snapshot_parameter.elisa").read_text(), True),
    ("stale-current-field", BASE.replace("    store.flags[slot] <- false", "    store.flags[store.count] <- false"), False),
    ("rebound-copy", BASE.replace("slot: usize", "slot: mutable usize").replace("    store.flags[slot] <- false", "    slot <- 4\n    store.flags[slot] <- false"), False),
    ("wrong-entry-bound", BASE.replace("store.count >= 4", "store.count > 4"), False),
    ("changed-before-copy", BASE.replace("    slot: usize", "    store.count <- 4\n    slot: usize"), False),
    ("different-field", BASE.replace("    count: mutable usize", "    count: mutable usize\n    other: mutable usize").replace("slot: usize = store.count", "slot: usize = store.other"), False),
    ("fallthrough-guard", BASE.replace("    return if store.count >= 4", "    if store.count >= 4:\n        pass"), False),
)
with tempfile.TemporaryDirectory(prefix="scalar-copy-bounds-") as directory:
    for name, source, accepted in CASES:
        path = Path(directory) / (name + ".elisa")
        path.write_text(source)
        for route in ("--json", "--function-json"):
            command = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert report["summary"]["semantic_errors"] == 0, (name, route, report["summary"])
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"], report["replay"])
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
            else:
                assert report["summary"]["unproven"] > 0
        print(name, "accepted" if accepted else "refused")
