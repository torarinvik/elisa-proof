"""Repeated callees resolve from source without weakening spans or actuals."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """module A:
    public:
        def step(value: i64) -> i64:
            ensure result == value
            return value
        def caller(value: i64) -> i64:
            requires value >= 1 and value <= 100
            ensure result == value
            return step(value)
module B:
    public:
        def step(value: i64) -> i64:
            ensure result == value + 1
            return value + 1
"""
for name, source, accepted in (
    ("same-module", BASE, True),
    ("qualified", BASE.replace("return step(value)", "return A::step(value)"), True),
    ("wrong-module", BASE.replace("return step(value)", "return B::step(value)"), False),
    ("changed-argument", BASE.replace("return step(value)", "return step(value + 1)"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["caller"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            # Focused verification currently leaves repeated module callees unverified.
            # Keep its conservative refusal explicit; full JSON qualifies the dependencies.
            expected_acceptance = accepted and route == "--json"
            assert run.returncode == (0 if expected_acceptance else 1), (name, route, report["summary"])
            if route == "--function-json":
                assert any(f["kind"] == "function-summary-unverified" for f in report["findings"])
            assert report["summary"]["semantic_errors"] == 0
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
    print("same-module call replay:", name, "full report accepted" if accepted else "full report refused", "; focused module callee remains unverified")
