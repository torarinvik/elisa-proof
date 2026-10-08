"""Definite arithmetic traps must be refused across every source-bound CLI route."""
import test_source_admission_matrix as admission

admission.MALFORMED = {
    "division-by-zero": b"\ndef trap(raw: i64) -> i64:\n    return raw / 0\n",
    "modulo-by-zero": b"\ndef trap(raw: i64) -> i64:\n    return raw % 0\n",
    "oversized-shift": b"\ndef trap() -> i64:\n    value: i64 = 1\n    return value << 64\n",
    "negative-shift": b"\ndef trap() -> i64:\n    value: i64 = 1\n    return value << -2\n",
}
admission.main()


# Safe arithmetic, including a warning-only zero shift, remains admissible.
import json
from pathlib import Path
import tempfile

safe = b"""
def safe_division() -> i64:
    ensure result == 2
    return 4 / 2

def safe_modulo() -> i64:
    ensure result == 0
    return 4 % 2

def safe_shift() -> i64:
    ensure result == 2
    return 1 << 1

def zero_shift() -> i64:
    ensure result == 1
    return 1 << 0
"""
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    source = directory / "safe.elisa"
    source.write_bytes(admission.BASE + safe)
    proof = directory / "safe.proof"
    proof.write_bytes(admission.run("--proof", admission.GOAL, source).stdout)
    repaired = json.loads(admission.run("--repair", admission.GOAL, source).stdout)
    (directory / "control.script").write_text(repaired["script"])
    for name, arguments in admission.routes(directory, source, proof):
        process = admission.run(*arguments)
        assert process.returncode == 0, (name, process.stdout[:300])
print("Arithmetic admission: safe division, modulo and shifts preserve every CLI route")
