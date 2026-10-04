"""Literal range arithmetic keeps binder identity and conservative machine bounds."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for name, expected in (("loop_stride", 0), ("rejected_loop_stride", 1),
                       ("rejected_shadowed_stride", 1), ("rejected_loop_machine_overflow", 1)):
    run = subprocess.run([BIN, "--function-json", name,
                          str(ROOT / "examples/loop_stride_width.elisa")],
                         capture_output=True, text=True, timeout=60)
    report = json.loads(run.stdout)
    assert run.returncode == expected, (name, run.returncode, report.get("findings"), run.stderr)
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0
    assert report["replay"]["replayed"] == report["replay"]["certificates"]
    assert not report["trust"]["trusted_assumptions"]
    if expected == 0:
        assert report["status"] == "proved" and report["findings"] == []
    else:
        assert any(f["kind"] == "index-upper-unproven" for f in report["findings"])
print("literal loop stride replays; undersized arrays, shadowed binders and overflow reject")
