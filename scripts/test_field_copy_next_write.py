"""A source field-copy equation is live at the next pure indexed write only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """struct Store:
    count: mutable usize
    other: mutable usize
    flags: mutable bool[4]
def checked(store: mutable Store&) -> void:
    return if store.count >= 4
    slot: usize = store.count
    store.flags[slot] <- true
"""
for name, source, accepted in (
    ("immediate", BASE, True),
    ("mutable-immediate", BASE.replace("slot: usize", "slot: mutable usize"), True),
    ("region", BASE.replace("    slot: usize", "    region slot_scope:\n        slot: usize").replace("    store.flags[slot]", "        store.flags[slot]"), True),
    ("wide-entry", BASE.replace("count >= 4", "count > 4"), False),
    ("other-field", BASE.replace("slot: usize = store.count", "slot: usize = store.other"), False),
    ("rebound-copy", BASE.replace("slot: usize", "slot: mutable usize").replace("    store.flags[slot]", "    slot <- 4\n    store.flags[slot]"), False),
    ("changed-current-field", BASE.replace("    store.flags[slot]", "    store.count <- 4\n    store.flags[store.count]"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"], report["replay"])
            assert report["summary"]["semantic_errors"] == 0
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"] == 3
            else:
                assert report["findings"], (name, route, report["summary"])
    print("field copy:", name, "accepted" if accepted else "refused")
