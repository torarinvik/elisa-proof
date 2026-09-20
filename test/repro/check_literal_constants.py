"""Regressions for immutable literal constants and a frontend with tail returns."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
prover = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "build/elisa-proof"
for name, succeeds in [
    ("literal_constants_tail", True),
    ("literal_constants_shadow_parameter", False),
    ("literal_constants_shadow_local", False),
    ("literal_constants_usize_shadow_local", False),
    ("literal_constants_usize_shadow_call", False),
    ("literal_constants_false", False),
]:
    result = subprocess.run(
        [str(prover), "--json", str(root / "test/repro" / (name + ".elisa"))],
        capture_output=True, text=True, timeout=30,
    )
    report = json.loads(result.stdout)
    assert (result.returncode == 0) == succeeds, (name, result.stdout, result.stderr)
    if succeeds:
        assert report["summary"]["failed"] == 0
    else:
        assert report["summary"]["failed"] > 0
    if name.startswith("literal_constants_usize_shadow_"):
        assert report["verification_state"] != "proved"
        assert report["replay"]["certificates"] == report["replay"]["replayed"]
        assert report["replay"]["gaps"] == 0
    if succeeds:
        assert report["summary"]["semantic_errors"] == 0
        assert all(certificate["replayed"] for certificate in report["certificates"])
    print(name, "PASS")
