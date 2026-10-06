"""Typed numeric copies preserve only proved, pre-mutation scalar values."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def check(function, source, expected):
    run = subprocess.run(
        [BIN, "--function-json", function, str(ROOT / "examples" / source)],
        capture_output=True, text=True, timeout=60,
    )
    report = json.loads(run.stdout)
    assert run.returncode == expected, (function, run.returncode, report.get("findings"), run.stderr)
    assert report["summary"]["semantic_errors"] == 0, (function, report["summary"])
    assert report["replay"]["gaps"] == 0, (function, report["replay"])
    assert report["replay"]["certificates"] == report["replay"]["replayed"], (function, report["replay"])
    assert not report["trust"]["trusted_assumptions"], (function, report["trust"])
    if expected == 0:
        assert report["status"] == "proved" and report["findings"] == [], (function, report["findings"])
    else:
        assert report["status"] == "failed", (function, report["status"])
        assert any(f["kind"] == "ensure-unproven" and f["name"] == function for f in report["findings"]), report["findings"]


for function in (
    "copy_by_value",
    "copy_implicit_scalar_reference",
    "copy_explicit_scalar_reference_element",
    "copy_count_without_pop",
    "copy_count_before_pop",
    "copy_scalar_before_write",
):
    check(function, "numeric_copy_conversion.elisa", 0)

for function in (
    "reject_high_bit_unsigned_to_signed",
    "reject_narrowing_copy",
    "reject_mutated_scalar_poststate",
    "reject_mutated_count_poststate",
    "reject_unbounded_count_to_signed",
):
    check(function, "rejected_numeric_copy_conversion.elisa", 1)

print("numeric copies: typed snapshots prove; high-bit, narrowing and post-state claims refuse")
