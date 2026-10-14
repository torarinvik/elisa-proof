"""Opaque frame checks must honor a local callable that shadows a global name."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

BINARY = qualified_test_binary.proof_test_binary(ROOT)
SOURCE = ROOT / "examples/rejected_local_function_frame_shadow.elisa"

result = subprocess.run(
    [BINARY, "--json", str(SOURCE)], capture_output=True, text=True, timeout=60
)
report = json.loads(result.stdout)
assert result.returncode == 1, report
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert any(
    finding["kind"] == "frame-call-opaque" and finding["line"] == 11
    for finding in report["findings"]
), report["findings"]
assert report["summary"]["proven"] < report["summary"]["obligations"], report["summary"]

direct_source = """\
def dispatch(target: mutable i64&) -> void:
    return

def caller(target: mutable i64&) -> void changes target:
    dispatch(target)
"""
with tempfile.TemporaryDirectory(prefix="elisa-proof-global-frame-call-") as directory:
    direct_path = Path(directory) / "direct.elisa"
    direct_path.write_text(direct_source)
    direct_result = subprocess.run(
        [BINARY, "--json", str(direct_path)], capture_output=True, text=True, timeout=60
    )
    direct_report = json.loads(direct_result.stdout)
    assert direct_result.returncode == 0, direct_report
    assert direct_report["summary"]["proven"] == direct_report["summary"]["obligations"]
    assert direct_report["replay"]["gaps"] == 0
print("local function shadowing a global remains an opaque frame call")
