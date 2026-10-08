"""Void functions and assertions are source-derived obligations; value returns stay refused."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(os.environ.get("ELISA_PROOF_CONTROL_DIR", tempfile.mkdtemp(prefix="elisa-proof-void-assert-")))
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
    assert run.returncode == 0, (run.returncode, run.stdout[-500:], run.stderr[-300:])
    path = WORK / f"{source.stem}.package.json"
    path.write_text(run.stdout)
    return path


def correspond(bundle, source, expected_exit):
    run = subprocess.run([str(BINARY), "--correspondence", str(bundle), str(source)],
                         capture_output=True, text=True, timeout=300)
    (WORK / f"{source.stem}.correspondence.stdout").write_text(run.stdout)
    (WORK / f"{source.stem}.correspondence.stderr").write_text(run.stderr)
    (WORK / f"{source.stem}.correspondence.exit").write_text(f"{run.returncode}\n")
    assert run.returncode == expected_exit, (run.returncode, run.stdout[-800:], run.stderr[-300:])
    return json.loads(run.stdout)


def package_allow_unproved(source):
    run = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True,
                         text=True, timeout=300)
    (WORK / f"{source.stem}.package.stdout").write_text(run.stdout)
    (WORK / f"{source.stem}.package.stderr").write_text(run.stderr)
    (WORK / f"{source.stem}.package.exit").write_text(f"{run.returncode}\n")
    assert run.returncode in (0, 1), (run.returncode, run.stdout[-800:], run.stderr[-400:])
    path = WORK / f"{source.stem}.package.json"
    path.write_text(run.stdout)
    return path


positive = write("positive", """def reflexive(value: i64):
    assert value == value
""")
bundle = package(positive)
package_report = json.loads(bundle.read_text())
assert any(theorem["name"] == "reflexive" and theorem["line"] == 2
           for theorem in package_report["theorems"]), package_report
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

false_assert = write("false_assert", """def impossible(value: i64):
    assert value != value
""")
false_bundle = package_allow_unproved(false_assert)
false_report = json.loads(false_bundle.read_text())
assert not any(theorem["name"] == "impossible" and theorem["line"] == 2
               for theorem in false_report.get("theorems", [])), false_report
report = correspond(false_bundle, false_assert, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert (report["functions"][0]["status"], report["functions"][0]["reason"]) == (
    "unmatched", "unproved-obligation"), report

value_return = write("value_return", positive.read_text() + "    return value\n")
report = correspond(bundle, value_return, 1)
assert report["source_admissible"] is False and report["package"]["status"] == "replayed", report
assert report["summary"]["checked"] == 0 and report["summary"]["coverage"] == "not-established", report

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
