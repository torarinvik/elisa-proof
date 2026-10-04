"""Invalid explicit runtime paths are rejected before snapshots and compilation."""
import os
from pathlib import Path
import subprocess
import tempfile

if not __debug__:
    raise SystemExit("runtime input checks must run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
compiler = Path(os.environ.get("ELISA_COMPILER_BIN",
                              ROOT.parent / "Elisa-compiler/scripts/elisac_stage1.sh"))
assert compiler.is_file() and os.access(compiler, os.X_OK), compiler
with tempfile.TemporaryDirectory(prefix="elisa-runtime-input-") as directory:
    missing = Path(directory) / "missing-runtime.o"
    environment = dict(os.environ, ELISA_COMPILER_BIN=str(compiler),
                       ELISA_RUNTIME_OBJ=str(missing))
    run = subprocess.run(["bash", str(ROOT / "scripts/build.sh")], cwd=ROOT,
                         env=environment, capture_output=True, text=True, timeout=15)
    assert run.returncode == 2, (run.returncode, run.stdout, run.stderr)
    assert run.stdout == "", run.stdout
    assert run.stderr == "Elisa runtime object not found: %s\n" % missing, run.stderr
print("build runtime inputs: missing explicit runtime refused before compiler work")
