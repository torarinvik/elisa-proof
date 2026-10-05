"""Direct package-reader regression for lossy JSON-number decoding."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from portable_replay_support import BINARY, REPLAY

INPUT_LIMIT = 64 * 1024 * 1024


def run_bytes(data, path):
    path.write_bytes(data)
    process = subprocess.run([str(REPLAY), str(path)], capture_output=True, timeout=120)
    result = json.loads(process.stdout)
    return process, result


def assert_package_refusal(process, result, status, reason):
    assert process.returncode == 1, (process.returncode, result, process.stderr)
    assert result["status"] == status and result["reason"] == reason, result
    assert result["theorems"] == [], result
    assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, result


def main():
    exported = subprocess.run([str(BINARY), "--package", str(ROOT / "examples/verified.elisa")],
                              capture_output=True, timeout=120)
    assert exported.returncode == 0, (exported.returncode, exported.stderr)
    package = json.loads(exported.stdout)
    assert package["theorems"]

    with tempfile.TemporaryDirectory(prefix="elisa-proof-package-number-encoding-") as directory:
        work = Path(directory)

        # Positive control: clean integer-encoded package is freshly replayed by the selected
        # producer/replay generation pair.
        positive, positive_result = run_bytes(exported.stdout, work / "positive.json")
        assert positive.returncode == 0 and positive_result["status"] == "replayed", positive_result
        assert positive_result["summary"] == {
            "theorems": len(package["theorems"]),
            "replayed": len(package["theorems"]),
            "not_replayed": 0,
        }, positive_result

        # A fractional conclusion index rounds to its original integer in the JSON DOM's f64
        # representation. It must be malformed before any theorem can be published.
        raw = exported.stdout
        fractional, replacements = re.subn(
            rb'("conclusion":)([0-9]+)',
            lambda match: match.group(1) + match.group(2) + b"." + b"0" * 80 + b"1",
            raw,
            count=1,
        )
        assert replacements == 1
        rejected, rejected_result = run_bytes(fractional, work / "fractional-index.json")
        assert_package_refusal(rejected, rejected_result, "malformed", "number-format")

        # A package-wide copied-string budget error is over-budget, distinct from malformed
        # schema and theorem rejection, and cannot leak already parsed theorem results.
        over_budget = json.loads(exported.stdout)
        old_name = over_budget["kernel"]["nodes"][0]["name"]
        copied = sum(len(node[field].encode("utf-8"))
                     for node in over_budget["kernel"]["nodes"]
                     for field in ("kind", "operator", "name", "secondary_name"))
        replacement_size = 65536 - (copied - len(old_name.encode("utf-8"))) + 1
        assert 0 < replacement_size <= 65536, (copied, replacement_size)
        over_budget["kernel"]["nodes"][0]["name"] = "x" * replacement_size
        budget_process, budget_result = run_bytes(
            json.dumps(over_budget, separators=(",", ":")).encode(), work / "string-budget.json")
        assert_package_refusal(budget_process, budget_result, "over-budget", "string-budget")

        # A well-formed theorem with a bad identity is rejected (not malformed/over-budget) and
        # is reported as rejected, while the package exit remains unsuccessful.
        rejected_theorem = json.loads(exported.stdout)
        rejected_theorem["theorems"][0]["goal_fingerprint"] += 1
        theorem_process, theorem_result = run_bytes(
            json.dumps(rejected_theorem, separators=(",", ":")).encode(), work / "bad-fingerprint.json")
        assert theorem_process.returncode == 1 and theorem_result["status"] == "rejected", theorem_result
        assert theorem_result["reason"] == "fingerprint-mismatch", theorem_result
        assert theorem_result["theorems"][0]["status"] == "rejected", theorem_result

        # A file one byte beyond the shared input cap is refused by bounded file reading before
        # the JSON parser allocates a DOM. This is an unreadable-input exit, not a package verdict.
        oversized_path = work / "input-over-cap.json"
        with oversized_path.open("wb") as oversized:
            oversized.seek(INPUT_LIMIT)
            oversized.write(b" ")
        oversized_process = subprocess.run([str(REPLAY), str(oversized_path)],
                                           capture_output=True, timeout=120)
        oversized_result = json.loads(oversized_process.stdout)
        assert oversized_process.returncode == 2 and oversized_result["status"] == "unreadable", oversized_result
        assert len(oversized_process.stdout) < 4096, len(oversized_process.stdout)

    print("portable package numeric encoding: exact positive replay; rounded fractional index malformed; "
          "budget/rejection classes distinct; package-wide failures publish no theorem; input cap enforced")


if __name__ == "__main__":
    main()
