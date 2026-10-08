"""Exclusive-reference value threading remains outside source correspondence."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-exclusive-refusal-"))
SOURCE = WORK / "threaded_refusal.elisa"
SOURCE.write_text("""def bump(value: mutable usize&) -> void:
    return

def caller() -> usize:
    ensure result == 5
    x: mutable usize = 5
    bump(&x)
    return x
""")
package = subprocess.run([str(BINARY), "--package", str(SOURCE)], capture_output=True, text=True, timeout=300)
assert package.returncode == 0, (package.stdout[-1000:], package.stderr[-500:])
PACKAGE = WORK / "threaded_refusal.pkg.json"
PACKAGE.write_text(package.stdout)
result = subprocess.run([str(BINARY), "--correspondence", str(PACKAGE), str(SOURCE)], capture_output=True, text=True, timeout=300)
assert result.returncode == 1, (result.returncode, result.stdout[-1200:], result.stderr[-500:])
report = json.loads(result.stdout)
assert report["package"]["status"] == "replayed" and report["source_admissible"] is True, report
assert [(item["name"], item["status"], item["reason"]) for item in report["functions"]] == [
    ("bump", "unsupported", "parameter-type"),
    ("caller", "unsupported", "callee-unchecked"),
], report
assert report["summary"]["checked"] == 0, report
