"""Require exact output on partial writes, and refusal on failed output.

Run against a separately provenance-validated native proof product. The syscall
shim is test-only; macOS marks its direct syscall interface deprecated.
"""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/elisa-proof"
system = platform.system()
if system not in ("Darwin", "Linux"):
    raise SystemExit("output-write regression requires macOS or Linux")
command = [str(binary), "--json", str(ROOT / "examples/arithmetic_identity.elisa")]
environment = os.environ.copy()
for key in ("LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "ELISA_TEST_WRITE_MODE"):
    environment.pop(key, None)

def run(env):
    return subprocess.run(command, env=env, capture_output=True, timeout=30)

baseline = run(environment)
assert baseline.returncode == 0, baseline.stderr[-1000:]
assert json.loads(baseline.stdout)["status"] == "proved"
with tempfile.TemporaryDirectory(prefix="proof-output-write-") as directory:
    library = Path(directory) / ("hook.dylib" if system == "Darwin" else "hook.so")
    flags = ["-dynamiclib"] if system == "Darwin" else ["-shared", "-fPIC"]
    subprocess.run([os.environ.get("CC", "clang"), *flags, "-o", str(library),
                    str(ROOT / "scripts/fixtures/output_write_interpose.c")], check=True)
    preload = "DYLD_INSERT_LIBRARIES" if system == "Darwin" else "LD_PRELOAD"
    failures = []
    for mode in ("partial", "zero", "error"):
        env = dict(environment, ELISA_TEST_WRITE_MODE=mode)
        env[preload] = str(library)
        result = run(env)
        if mode == "partial":
            if result.returncode != 0 or result.stdout != baseline.stdout:
                failures.append(f"partial: exit={result.returncode}, bytes={len(result.stdout)}, expected={len(baseline.stdout)}")
        elif result.returncode <= 0:
            failures.append(f"{mode}: expected deliberate nonzero refusal, got {result.returncode}")
    assert not failures, "; ".join(failures)
print("output write regression PASS: exact partial output; zero/error refusal")
