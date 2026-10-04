"""Representable literal sum caps require overflow-safe independent replay."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def run(fixture, expected, semantic_errors=0):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == expected, (result.returncode, report["findings"])
    assert report["summary"]["semantic_errors"] == semantic_errors, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    return report


positive = run("unsigned_literal_sum_cap.elisa", 0)
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0
negative = run("rejected_unsigned_literal_sum_cap.elisa", 1)
for target in ("false_tighter_sum", "byte_sum_without_bound"):
    assert any(f["name"] == target for f in negative["findings"]), target
    assert not any(d.get("name") == target and d.get("verified")
                   for d in negative["declaration_details"]), target
invalid = run("rejected_unsigned_literal_cap_width.elisa", 1, semantic_errors=1)
assert any(d["expected"] == "u8" and d["expected_count"] == 256
           and "does not fit" in d["message"] for d in invalid["semantic_diagnostics"])
assert not any(d.get("name") == "byte_cap_outside_width" and d.get("verified")
               for d in invalid["declaration_details"])
print("unsigned literal sum caps replay; false tighter, overflow and out-of-width caps reject")
