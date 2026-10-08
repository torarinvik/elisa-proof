"""Void functions and assertions are source-derived obligations; value returns stay refused."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-void-assert-"))


def write(name, text):
    path = WORK / f"{name}.elisa"
    path.write_text(text)
    return path


def package(source):
    run = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True,
                         text=True, timeout=300)
    assert run.returncode == 0, (run.returncode, run.stdout[-500:], run.stderr[-300:])
    path = WORK / f"{source.stem}.package.json"
    path.write_text(run.stdout)
    return path


def correspond(bundle, source, expected_exit):
    run = subprocess.run([str(BINARY), "--correspondence", str(bundle), str(source)],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == expected_exit, (run.returncode, run.stdout[-800:], run.stderr[-300:])
    return json.loads(run.stdout)


positive = write("positive", """def reflexive(value: i64):
    assert value == value
""")
bundle = package(positive)
report = correspond(bundle, positive, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert len(report["functions"]) == 1, report
assert (report["functions"][0]["status"], report["functions"][0]["obligations"],
        report["functions"][0]["matched"]) == ("checked", 1, 1), report

changed = write("changed", positive.read_text().replace("value == value", "value != value"))
report = correspond(bundle, changed, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert (report["functions"][0]["status"], report["functions"][0]["reason"]) == (
    "unmatched", "unproved-obligation"), report

value_return = write("value_return", positive.read_text() + "    return value\n")
report = correspond(bundle, value_return, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert (report["functions"][0]["status"], report["functions"][0]["reason"]) == (
    "unsupported", "return-type"), report

early = write("early_void", """def early(flag: bool) -> void:
    ensure flag == flag
    if flag:
        return
""")
early_bundle = package(early)
report = correspond(early_bundle, early, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
entry = report["functions"][0]
assert entry["status"] == "checked" and entry["obligations"] >= 2 and entry["matched"] == entry["obligations"], report

print("assert-only and early void ensures check; changed assertions and inferred value returns refuse")
