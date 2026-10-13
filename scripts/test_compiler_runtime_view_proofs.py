"""Replay compiler StringView range and slice refinement proofs."""
import subprocess
import sys
from pathlib import Path


PROOF_ROOT = Path(__file__).resolve().parents[1]
COMPILER_ROOT = PROOF_ROOT.parent / "Elisa-compiler"
CHECKERS = (
    COMPILER_ROOT / "test/proofs/check_bytes_view_range_ref.py",
    COMPILER_ROOT / "test/proofs/check_string_view_slice_semantics.py",
)

for checker in CHECKERS:
    run = subprocess.run([sys.executable, str(checker)], capture_output=True,
                         text=True, timeout=300)
    if run.returncode != 0:
        sys.stderr.write(run.stderr)
        sys.stderr.write(run.stdout)
        raise SystemExit(run.returncode)
    sys.stdout.write(run.stdout)
