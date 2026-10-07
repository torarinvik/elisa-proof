"""Signed call-result locals retain identity through reconstructed later calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
base = (ROOT / "examples/conditional_join.elisa").read_text()
cases = [
    ("ordinary-local", base, True),
    ("qualified-calls", base.replace("step(t)", "ConditionalJoin::step(t)").replace("finish(n, end)", "ConditionalJoin::finish(n, end)"), True),
    ("rejected-join", (ROOT / "examples/rejected_conditional_join.elisa").read_text(), False),
    ("rejected-loop-state", (ROOT / "examples/rejected_loop_state_joins.elisa").read_text(), False),
]
for name, source, accepted in cases:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "probe.elisa"
        path.write_text(source)
        run = subprocess.run([BINARY, "--json", str(path)], capture_output=True, text=True, timeout=60)
        report = json.loads(run.stdout)
        assert run.returncode == (0 if accepted else 1), (name, report["status"])
        assert report["summary"]["semantic_errors"] == 0, name
        assert report["replay"]["gaps"] == 0, (name, report["replay"])
        assert not report["trust"]["trusted_assumptions"], name
        if accepted:
            assert report["summary"]["obligations"] == report["summary"]["proven"] == 22
        else:
            assert report["summary"]["proven"] < report["summary"]["obligations"]
    print("signed call snapshots:", name, "accepted" if accepted else "refused")
