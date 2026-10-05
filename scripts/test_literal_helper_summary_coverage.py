"""Literal comparison helpers must retain complete independently replayed summaries."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
for name in ("proof_kernel_replay_integer_values_compare",
             "proof_kernel_replay_nonnegative_literal_constant",
             "proof_kernel_replay_signed_literal_comparison_constant"):
    process = subprocess.run(
        [binary, "--function-json", name,
         str(root / "examples/kernel_replay_standalone.elisa")],
        capture_output=True, text=True, timeout=120,
    )
    assert process.returncode == 0, (name, process.returncode, process.stderr)
    report = json.loads(process.stdout)
    assert report["status"] == "proved", (name, report["status"])
    assert report["summary"]["semantic_errors"] == 0, (name, report["summary"])
    assert report["summary"]["obligations"] == report["summary"]["proven"] > 0
    assert report["findings"] == [], (name, report["findings"])
    assert report["replay"]["gaps"] == 0, (name, report["replay"])
    assert report["replay"]["certificates"] == report["replay"]["replayed"] == report["summary"]["proven"]
    assert not report["trust"]["trusted_assumptions"]
    assert any(row["kind"] == "function" and row["name"] == name and row["verified"]
               for row in report["declaration_details"]), name
print("literal helpers: complete verified summaries replay within unchanged analysis caps")
