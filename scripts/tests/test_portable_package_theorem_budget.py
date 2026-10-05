"""Portable theorem count cap accepts the exact limit and refuses one over up front."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
# The test lives below scripts/, so expose the shared resolver before importing it.
# It selects both executables from one published generation, or accepts a complete
# explicit pair through ELISA_PROOF_BIN and ELISA_PROOF_REPLAY_BIN.
sys.path.insert(0, str(ROOT / "scripts"))
from portable_replay_support import BINARY as PROOF, REPLAY

THEOREM_LIMIT = 65536


def replay(package, path):
    path.write_text(json.dumps(package, separators=(",", ":")), encoding="utf-8")
    return subprocess.run([str(REPLAY), str(path)], capture_output=True, timeout=180)


def main():
    exported = subprocess.run(
        [str(PROOF), "--package", str(ROOT / "examples/verified.elisa")],
        capture_output=True, timeout=120,
    )
    assert exported.returncode == 0, exported.stderr.decode(errors="replace")
    package = json.loads(exported.stdout)
    assert package["theorems"]
    theorem = package["theorems"][0]

    with tempfile.TemporaryDirectory(prefix="elisa-proof-theorem-budget-") as directory:
        path = Path(directory) / "package.json"

        exact = dict(package)
        exact["theorems"] = [theorem] * THEOREM_LIMIT
        accepted = replay(exact, path)
        accepted_result = json.loads(accepted.stdout)
        assert accepted.returncode == 0, accepted_result
        assert accepted_result["status"] == "replayed", accepted_result
        assert accepted_result["summary"] == {
            "theorems": THEOREM_LIMIT,
            "replayed": THEOREM_LIMIT,
            "not_replayed": 0,
        }, accepted_result["summary"]

        over = dict(package)
        over["theorems"] = [theorem] * (THEOREM_LIMIT + 1)
        refused = replay(over, path)

    result = json.loads(refused.stdout)
    assert refused.returncode == 1, (refused.returncode, result)
    assert len(refused.stdout) < 4096, len(refused.stdout)
    assert result["status"] == "over-budget" and result["reason"] == "theorem-budget", result
    assert result["theorems"] == [], result["theorems"]
    assert result["summary"] == {
        "theorems": 0,
        "replayed": 0,
        "not_replayed": 0,
    }, result["summary"]


if __name__ == "__main__":
    main()
    print("portable theorem count budget: exact cap replays; one over is refused before theorem replay")
