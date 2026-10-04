"""An include line the reference compiler and the self-hosted driver expand differently must
make the import fail: certifying either reading certifies a program the other compiler builds
differently (examples/include_driver_divergence/*.elisa)."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
CASES = ROOT / "examples/include_driver_divergence"


def report(name):
    run = subprocess.run([str(BINARY), "--json", str(CASES / name)], capture_output=True, text=True, timeout=120)
    return run.returncode, json.loads(run.stdout)


status, control = report("control.elisa")
assert status == 0 and control["status"] == "proved", (status, control["status"])
for name in ("tab_separator.elisa", "trailing_text.elisa", "empty_then_body.elisa", "indented_directive.elisa"):
    status, divergent = report(name)
    assert status == 1, (name, status)
    assert divergent["status"] != "proved" and divergent["verification_state"] != "proved", (name, divergent["status"])
    assert any(f["kind"] == "import-error" for f in divergent["findings"]), (name, divergent["findings"])
print("include lines the two compilers expand differently fail the import")
