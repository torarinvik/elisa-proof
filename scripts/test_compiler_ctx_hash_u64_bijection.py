"""Replay full-width ctx_hash_u64 inverse and collision proof claims."""
import subprocess
import sys
from pathlib import Path


PROOF_ROOT = Path(__file__).resolve().parents[1]
COMPILER_ROOT = PROOF_ROOT.parent / "Elisa-compiler"
CHECKER = COMPILER_ROOT / "test/proofs/check_ctx_hash_u64_bijection.py"
run = subprocess.run([sys.executable, str(CHECKER)], capture_output=True,
                     text=True, timeout=300)
if run.returncode != 0:
    sys.stderr.write(run.stderr)
    sys.stderr.write(run.stdout)
    raise SystemExit(run.returncode)
sys.stdout.write(run.stdout)
