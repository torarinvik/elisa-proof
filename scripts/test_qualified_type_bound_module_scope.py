"""Qualified scalar type witnesses resolve from the source root inside module bodies."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, report = run("module_u32_scoped_constant_branch.elisa")
assert code == 0 and report["status"] == "proved", report
assert report["summary"]["proven"] == report["summary"]["obligations"] == 3
assert report["replay"]["gaps"] == 0

code, report = run("rejected_module_u32_scoped_constant_branch.elisa")
assert code == 1 and report["status"] == "failed", report
assert report["replay"]["gaps"] == 0
assert any(finding["kind"] == "ensure-unproven" for finding in report["findings"])

print("qualified u32 type-bound lookup proves inside module/extend and rejects the wrong value")
