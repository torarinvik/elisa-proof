"""Expanding a checked Boolean helper preserves conjunction order and source identity."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-and-assoc-"))


def write(name, text):
    path = WORK / f"{name}.elisa"
    path.write_text(text)
    return path


def package(source):
    run = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True,
                         text=True, timeout=300)
    assert run.returncode == 0, (run.returncode, run.stdout[-800:], run.stderr[-400:])
    path = WORK / f"{source.stem}.package.json"
    path.write_text(run.stdout)
    return path


def correspond(bundle, source, expected_exit):
    run = subprocess.run([str(BINARY), "--correspondence", str(bundle), str(source)],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == expected_exit, (run.returncode, run.stdout[-1000:], run.stderr[-400:])
    return json.loads(run.stdout)


positive = write("positive", """module HelperPolicy:
    public:
        def combine(second: bool, third: bool) -> bool:
            ensure result == (second and third)
            return second and third

def caller(first: bool, second: bool, third: bool) -> bool:
    ensure result == (first and second and third)
    return first and HelperPolicy::combine(second, third)
""")
bundle = package(positive)
report = correspond(bundle, positive, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert [(item["owner"], item["name"], item["status"]) for item in report["functions"]] == [
    (["HelperPolicy"], "combine", "checked"), ([], "caller", "checked")
], report

changed = write("changed", positive.read_text().replace(
    "ensure result == (second and third)", "ensure result == (second or third)", 1))
report = correspond(bundle, changed, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert [(item["name"], item["status"], item["reason"]) for item in report["functions"]] == [
    ("combine", "unmatched", "unproved-obligation"),
    ("caller", "unsupported", "callee-unchecked"),
], report

reordered = write("reordered", positive.read_text().replace(
    "HelperPolicy::combine(second, third)", "HelperPolicy::combine(third, second)"))
report = correspond(bundle, reordered, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
caller = next(item for item in report["functions"] if item["name"] == "caller")
assert (caller["status"], caller["reason"]) == ("unmatched", "unproved-obligation"), report

wrong_owner = write("wrong_owner", positive.read_text().replace(
    "HelperPolicy::combine(second, third)", "OtherPolicy::combine(second, third)") + """

module OtherPolicy:
    public:
        def combine(second: bool, third: bool) -> bool:
            ensure result == false
            return false
""")
report = correspond(bundle, wrong_owner, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
caller = next(item for item in report["functions"] if item["name"] == "caller")
assert (caller["status"], caller["reason"]) == ("unsupported", "callee-unchecked"), report

print("Boolean helper expansion matches ordered conjunctions; changed and wrong-owner helpers refuse")
