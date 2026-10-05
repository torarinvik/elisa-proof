"""Portable proof package decoder bounds the complete copied string pool."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
# This test lives below scripts/, so add its parent explicitly before importing the
# shared resolver. It pins both binaries to one published generation (or honors a
# complete paired override) at import time.
sys.path.insert(0, str(ROOT / "scripts"))
from portable_replay_support import BINARY as PROOF, REPLAY


def run(command):
    return subprocess.run(command, capture_output=True, check=False, timeout=120)


def main():
    exported = run([str(PROOF), "--package", str(ROOT / "examples/verified.elisa")])
    assert exported.returncode == 0, exported.stderr.decode(errors="replace")
    package = json.loads(exported.stdout)
    assert package["theorems"], "the positive fixture must contain a replayable theorem"

    def append_string_node(target, byte):
        target["kernel"]["nodes"].append({
            "kind": "string", "operator": "", "left": 0, "right": 0,
            "auxiliary": 0, "children_start": 0, "children_count": 0,
            "value": "0", "name": byte * 40000, "secondary_name": "",
        })

    # One 40 KiB node string remains within the package budget.
    under_budget = copy.deepcopy(package)
    append_string_node(under_budget, "a")

    with tempfile.TemporaryDirectory(prefix="elisa-proof-package-budget-") as work:
        path = Path(work) / "package.json"
        path.write_text(json.dumps(under_budget), encoding="utf-8")
        checked = run([str(REPLAY), str(path)])
        assert checked.returncode == 0, checked.stdout.decode(errors="replace")
        assert json.loads(checked.stdout)["status"] == "replayed"

        # Each name is individually below STRING_BYTES (65536), but the two strings
        # together exceed the intended package-wide copied-string budget. Scalar strings
        # are legal disconnected arena nodes, so the original theorem still fully replays.
        over_budget = copy.deepcopy(under_budget)
        append_string_node(over_budget, "b")
        path.write_text(json.dumps(over_budget), encoding="utf-8")
        checked = run([str(REPLAY), str(path)])

    result = json.loads(checked.stdout)
    assert checked.returncode == 1, (checked.returncode, result)
    assert result["status"] == "over-budget", result
    assert result["reason"] == "string-budget", result


if __name__ == "__main__":
    main()
    print("portable package aggregate string budget: over-budget input refused")
