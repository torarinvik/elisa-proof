"""Source-owned const-enum casts resolve by exact owner and literal value."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(os.environ.get("ELISA_PROOF_CONTROL_DIR", tempfile.mkdtemp(prefix="elisa-proof-enum-owner-")))
WORK.mkdir(parents=True, exist_ok=True)


def write(name, text):
    path = WORK / f"{name}.elisa"
    path.write_text(text)
    return path


def package(source):
    run = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True,
                         text=True, timeout=300)
    (WORK / f"{source.stem}.package.stdout").write_text(run.stdout)
    (WORK / f"{source.stem}.package.stderr").write_text(run.stderr)
    (WORK / f"{source.stem}.package.exit").write_text(f"{run.returncode}\n")
    assert run.returncode == 0, (run.returncode, run.stdout[-800:], run.stderr[-400:])
    path = WORK / f"{source.stem}.package.json"
    path.write_text(run.stdout)
    return path


def correspond(bundle, source, expected_exit):
    run = subprocess.run([str(BINARY), "--correspondence", str(bundle), str(source)],
                         capture_output=True, text=True, timeout=300)
    (WORK / f"{source.stem}.correspondence.stdout").write_text(run.stdout)
    (WORK / f"{source.stem}.correspondence.stderr").write_text(run.stderr)
    (WORK / f"{source.stem}.correspondence.exit").write_text(f"{run.returncode}\n")
    assert run.returncode == expected_exit, (run.returncode, run.stdout[-1000:], run.stderr[-400:])
    return json.loads(run.stdout)


positive = write("positive", """module Worker:
    const enum Status of i64:
        InvalidJob = -100

    def wire() -> i64:
        ensure result == -100
        return Status.InvalidJob.i64()
""")
bundle = package(positive)
report = correspond(bundle, positive, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
wire = next(item for item in report["functions"] if item["name"] == "wire")
assert wire["status"] == "checked" and wire["obligations"] == wire["matched"] == 1, report

scope_form = write("scope_form", positive.read_text().replace(
    "Status.InvalidJob.i64()", "Worker::Status::InvalidJob.i64()"))
scope_bundle = package(scope_form)
report = correspond(scope_bundle, scope_form, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
wire = next(item for item in report["functions"] if item["name"] == "wire")
assert wire["status"] == "checked" and wire["obligations"] == wire["matched"] == 1, report

changed_value = write("changed_value", positive.read_text().replace("InvalidJob = -100", "InvalidJob = -101"))
report = correspond(bundle, changed_value, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
wire = next(item for item in report["functions"] if item["name"] == "wire")
assert (wire["status"], wire["reason"]) == ("unmatched", "unproved-obligation"), report

wrong_owner = write("wrong_owner", """module Worker:
    const enum Status of i64:
        InvalidJob = -100

    def wire() -> i64:
        ensure result == -100
        return Other::Status.InvalidJob.i64()

module Other:
    const enum Status of i64:
        InvalidJob = -101
""")
report = correspond(bundle, wrong_owner, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
wire = next(item for item in report["functions"] if item["name"] == "wire")
assert (wire["status"], wire["reason"]) == ("unmatched", "unproved-obligation"), report

custom_cast = write("custom_cast", positive.read_text().replace(
    "    def wire() -> i64:",
    "    def i64(self: Status) -> i64:\n        return 7\n\n    def wire() -> i64:"))
report = correspond(bundle, custom_cast, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
wire = next(item for item in report["functions"] if item["name"] == "wire")
assert wire["status"] == "unsupported" or wire["reason"] == "callee-unchecked", report

wrong_width = write("wrong_width", """module Worker:
    const enum Status of u8:
        InvalidJob = 156

    def wire() -> i64:
        ensure result == 156
        return Status.InvalidJob.i64()
""")
wrong_width_bundle = package(wrong_width)
report = correspond(wrong_width_bundle, wrong_width, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
wire = next(item for item in report["functions"] if item["name"] == "wire")
assert wire["status"] == "unsupported" or wire["reason"] == "callee-unchecked", report

print("Const-enum return facts bind exact owners and values; changed-value, wrong-owner, and custom-cast controls refuse")
