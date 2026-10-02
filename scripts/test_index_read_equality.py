"""Same-array reads require independently established machine-index equality."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, expected in (("index_read_equality.elisa", "proved"),
                          ("open_indexed_prefix_reasoning.elisa", "proved"),
                          ("rejected_index_read_equality.elisa", "failed")):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == (0 if expected == "proved" else 1)
    assert report["status"] == expected, report["findings"]
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    if expected == "proved":
        assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
    else:
        for target in ("rejected_different_index", "rejected_different_array", "rejected_wrapping_index",
                       "rejected_stale_read_after_write", "rejected_skipped_prefix_row",
                       "rejected_float_arithmetic_totality"):
            # Float arithmetic may fail closed at proposition typing before
            # reaching the integer-only denial rule; it must never be verified.
            rejected_kinds = {"ensure-unproven", "contract-proposition-type"} if target == "rejected_float_arithmetic_totality" else {"ensure-unproven"}
            assert any(f["name"] == target and f["kind"] in rejected_kinds
                       for f in report["findings"]), (target, report["findings"])
            assert not any(d.get("name") == target and d.get("verified")
                           for d in report["declaration_details"])
print("same-array indexed equalities replay; different indices, arrays, wrapping and stale-read controls reject")
