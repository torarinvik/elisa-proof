"""Record the open copy-bound defect and controls; not a passing acceptance gate."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "test/repro/scalar_field_snapshot_bound.elisa").read_text()
CASES = {
    "field-copy-open": (BASE, 2, 1),
    "local-guard": ((ROOT / "test/repro/scalar_field_snapshot_local_guard.elisa").read_text(), 0, 0),
    "parameter": ((ROOT / "test/repro/scalar_field_snapshot_parameter.elisa").read_text(), 0, 0),
    "stale-field": (BASE.replace("    store.flags[slot] <- false", "    store.flags[store.count] <- false"), 3, 1),
    "mutable-copy-rebound": (BASE.replace("slot: usize", "slot: mutable usize").replace("    store.flags[slot] <- false", "    slot <- 4\n    store.flags[slot] <- false"), 2, 1),
    "wrong-entry-bound": (BASE.replace("store.count >= 4", "store.count > 4"), 2, 0),
}
with tempfile.TemporaryDirectory(prefix="elisa-field-snapshot-") as directory:
    for name, (source, unproven, gaps) in CASES.items():
        path = Path(directory) / (name + ".elisa")
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (1 if unproven else 0), (name, route, report["summary"])
            assert report["summary"]["semantic_errors"] == 0
            assert report["summary"]["unproven"] == unproven, (name, route, report["summary"])
            assert report["replay"]["gaps"] == gaps, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            print(name, route, report["summary"])
