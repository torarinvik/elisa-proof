"""Built-in numeric casts keep surrounding primitive comparisons admissible."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/numeric_cast_operator.elisa"
run = subprocess.run([str(BINARY), "--json", str(SOURCE)],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 0, (run.returncode, run.stderr, run.stdout)
data = json.loads(run.stdout)
assert data["summary"]["semantic_errors"] == 0, data
assert data["replay"]["gaps"] == 0, data
assert data["replay"]["certificates"] == data["replay"]["replayed"], data
functions = {d["name"]: d for d in data["declaration_details"] if d.get("kind") == "function"}
for name in ("numeric_cast_request_status", "numeric_cast_effective"):
    assert functions[name]["verified"], functions[name]
    assert not any(f["name"] == name and f["kind"] in
                   ("expression-unsupported", "function-summary-unverified")
                   for f in data["findings"]), data

print("numeric casts: primitive comparisons and dependent function summaries verified and replayed")
