"""A front-end diagnostic leaves the verification state open; the report still says whether the
proof engine proved and replayed everything (`engine_state`, and a text line), and never claims
it did when a goal is open, the source is malformed, or no front-end diagnostic was raised."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path, *flags):
    return subprocess.run([str(BINARY), *flags, str(path)], capture_output=True, text=True, timeout=120).stdout


def report(path):
    return json.loads(run(path, "--json"))


LINE = "front end diagnostic, engine: proved"

proved = ROOT / "examples/front_end_diagnostic_engine_proved.elisa"
data = report(proved)
assert data["status"] == "failed" and data["verification_state"] == "unknown", data["status"]
assert data["engine_state"] == "proved" and data["summary"]["semantic_errors"] == 1
assert data["findings"] == [] and data["replay"]["gaps"] == 0
assert LINE in run(proved)

opened = ROOT / "examples/rejected_front_end_diagnostic_engine_open.elisa"
data = report(opened)
assert data["engine_state"] == "open", data["engine_state"]
assert sorted((f["kind"], f["line"]) for f in data["findings"]) == [("ensure-unproven", 6)], data["findings"]
assert LINE not in run(opened)

clean = ROOT / "examples/literal_count.elisa"
data = report(clean)
assert data["engine_state"] == "proved" and data["verification_state"] == "proved"
assert LINE not in run(clean)

with tempfile.TemporaryDirectory() as scratch:
    malformed = Path(scratch) / "malformed.elisa"
    malformed.write_text("def broken(x: i8) -> i8\n    ensure result >= -128\n    return x\n")
    text = run(malformed)
    assert LINE not in text, text
    data = json.loads(run(malformed, "--json"))
    assert data["engine_state"] == "open" and data["status"] == "failed", data["engine_state"]

print("engine state: a front-end diagnostic no longer hides what the engine proved")
