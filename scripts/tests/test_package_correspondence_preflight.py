"""Check correspondence package ingress shares portable replay's bounded JSON preflight."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys_path = str(ROOT / "scripts")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
from portable_replay_support import BINARY

SOURCE = ROOT / "examples/branch_negation.elisa"
FORMAT = "elisa-proof-correspondence-v1"
DEPTH_LIMIT = 256
INPUT_LIMIT = 64 * 1024 * 1024
SCAN_FACTOR = 8
OUTPUT_LIMIT = 64 * 1024
WALL_LIMIT_SECONDS = 30


def assert_fresh_stage1():
    manifest = json.loads(Path(str(BINARY) + ".manifest.json").read_text(encoding="utf-8"))
    compiler = manifest["compiler"]
    assert compiler["stage"] == "stage1", compiler
    product = Path(compiler["product"]["path"])
    assert hashlib.sha256(product.read_bytes()).hexdigest() == compiler["product"]["sha256"], compiler
    check = product.parents[1] / "scripts/assert_stage1_fresh.sh"
    result = subprocess.run(["bash", str(check), str(product)], capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == 0, result.stderr[-2000:]


def run(*arguments):
    started = time.monotonic()
    result = subprocess.run([str(BINARY), *map(str, arguments)], capture_output=True,
                            timeout=WALL_LIMIT_SECONDS)
    elapsed = time.monotonic() - started
    output_size = len(result.stdout) + len(result.stderr)
    assert elapsed < WALL_LIMIT_SECONDS and output_size <= OUTPUT_LIMIT, (
        arguments, elapsed, output_size,
    )
    assert result.returncode in (0, 1), (result.returncode, result.stderr[-2000:])
    report = json.loads(result.stdout)
    assert report.get("format") == FORMAT, report
    return result.returncode, report


def nested_string(depth, total_bytes):
    prefix = b"[" * depth + b'"'
    suffix = b'"' + b"]" * depth
    padding = total_bytes - len(prefix) - len(suffix)
    assert padding >= 0, (depth, total_bytes)
    return prefix + b"x" * padding + suffix


def assert_package_wide_error(result, status, reason):
    code, report = result
    assert code == 1, report
    assert report["source_admissible"] is True, report
    assert report["package"] == {"status": status, "reason": reason, "theorems": 0, "replayed": 0}, report
    assert report["functions"] == [], report
    assert report["summary"] == {
        "checked": 0, "unmatched": 0, "unsupported": 0,
        "coverage": "not-established", "exit_code": 1,
    }, report


with tempfile.TemporaryDirectory(prefix="elisa-package-correspondence-preflight-") as directory:
    work = Path(directory)

    assert_fresh_stage1()

    # Generate an actual package, then make correspondence replay it in a separate process.
    package_run = subprocess.run([str(BINARY), "--package", str(SOURCE)], capture_output=True,
                                 timeout=WALL_LIMIT_SECONDS)
    assert package_run.returncode == 0, (package_run.returncode, package_run.stderr[-2000:])
    package = json.loads(package_run.stdout)
    assert package["theorems"], package
    positive_path = work / "positive.json"
    positive_path.write_bytes(package_run.stdout)
    code, positive = run("--correspondence", positive_path, SOURCE)
    assert code == 0 and positive["package"]["status"] == "replayed", positive
    assert positive["package"]["theorems"] == positive["package"]["replayed"] > 0, positive
    assert positive["summary"]["coverage"] == "complete", positive

    malformed_path = work / "malformed.json"
    malformed_path.write_bytes(b'{"format":')
    assert_package_wide_error(
        run("--correspondence", malformed_path, SOURCE), "malformed", "json",
    )

    invalid_utf8_path = work / "invalid-utf8.json"
    invalid_utf8_path.write_bytes(b'{"format":"elisa-proof-package-v1","x":"\xff"}')
    assert_package_wide_error(
        run("--correspondence", invalid_utf8_path, SOURCE), "malformed", "utf8",
    )

    noncanonical_number_path = work / "noncanonical-number.json"
    noncanonical_number_path.write_bytes(b'{"format":"elisa-proof-package-v1","version":1.0}')
    assert_package_wide_error(
        run("--correspondence", noncanonical_number_path, SOURCE),
        "malformed", "number-format",
    )

    scan_budget = INPUT_LIMIT * SCAN_FACTOR
    exact_scan_size = scan_budget // DEPTH_LIMIT
    exact_scan_path = work / "exact-scan-bound.json"
    exact_scan_path.write_bytes(nested_string(DEPTH_LIMIT, exact_scan_size))
    assert_package_wide_error(
        run("--correspondence", exact_scan_path, SOURCE), "malformed", "package-schema",
    )

    # Depth 256 is accepted by the JSON parser. One byte beyond the shared depth-times-input
    # budget must be classified before DOM construction and publish no theorem rows.
    over_budget = nested_string(DEPTH_LIMIT, exact_scan_size + 1)
    over_path = work / "over-budget.json"
    over_path.write_bytes(over_budget)
    assert_package_wide_error(
        run("--correspondence", over_path, SOURCE), "over-budget", "json-scan-budget",
    )

    over_depth_path = work / "over-depth.json"
    over_depth_path.write_bytes(nested_string(DEPTH_LIMIT + 1, 2 * (DEPTH_LIMIT + 1) + 3))
    assert_package_wide_error(
        run("--correspondence", over_depth_path, SOURCE), "malformed", "json",
    )

    rejected = copy.deepcopy(package)
    rejected["source"]["admissible"] = False
    rejected_path = work / "rejected.json"
    rejected_path.write_text(json.dumps(rejected, separators=(",", ":")), encoding="utf-8")
    assert_package_wide_error(
        run("--correspondence", rejected_path, SOURCE), "rejected", "source-inadmissible",
    )

print("package correspondence preflight: fresh replay, UTF-8/numeric/nesting/scan bounds, and exact malformed/over-budget/rejected outcomes verified")
