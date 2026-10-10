"""Signed product growth is range-safe, nonnegative and non-strict."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """def checked(amount: i64, speed: i64) -> i64:
    requires amount >= 0 and amount <= 100
    requires speed >= 1 and speed <= 100
    ensure result >= amount
    return amount * speed
"""
for name, source, accepted in (
    ("bounded-product", BASE, True),
    ("commuted-product", BASE.replace("amount * speed", "speed * amount"), True),
    ("reversed-comparison", BASE.replace("result >= amount", "amount <= result"), True),
    ("zero-factor", BASE.replace("speed >= 1", "speed >= 0"), False),
    ("negative-base", BASE.replace("amount >= 0", "amount >= -100"), False),
    ("overflow", BASE.replace("i64", "i8"), False),
    ("no-upper-bound", BASE.replace(" and amount <= 100", ""), False),
    ("unsafe-bound-premise", BASE.replace("amount <= 100", "amount + 1 <= 101"), False),
    ("strict-result", BASE.replace("result >= amount", "result > amount"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            assert run.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert report["summary"]["semantic_errors"] == 0
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
    print("signed product growth:", name, "accepted" if accepted else "refused")
