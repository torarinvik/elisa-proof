"""Compact indexed protocol witnesses preserve snapshot limits and bounds refusal."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/operator_witness_snapshot_budget.elisa").read_text()
for name, source, accepted in (
    ("compact", BASE, True),
    ("wide-guard", BASE.replace("index >= 8", "index >= 9"), False),
    ("missing-guard", BASE.replace("    return if index >= 8\n", ""), False),
    ("shared-write", BASE.replace("store: mutable Store&", "store: Store&"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"] >= 11
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("operator witness snapshot:", name, "accepted" if accepted else "refused")
