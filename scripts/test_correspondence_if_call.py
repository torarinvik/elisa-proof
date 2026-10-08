"""Checked pure helper calls in branch conditions remain source-bound."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-if-call-"))


def write(name, text):
    path = WORK / f"{name}.elisa"
    path.write_text(text)
    return path


def package(source):
    result = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, (source, result.stdout[-800:], result.stderr[-400:])
    path = WORK / f"{source.stem}.pkg.json"
    path.write_text(result.stdout)
    return path


def correspond(bundle, source, expected_exit):
    result = subprocess.run([str(BINARY), "--correspondence", str(bundle), str(source)], capture_output=True, text=True, timeout=300)
    assert result.returncode == expected_exit, (result.returncode, result.stdout[-1000:], result.stderr[-400:])
    return json.loads(result.stdout)


positive = write("positive", """module HelperPolicy:
    public:
        def truth(value: i64) -> bool:
            requires value >= 0
            ensure result == true
            return true

def caller(value: i64) -> bool:
    requires value >= 0
    ensure result == true
    if HelperPolicy::truth(value):
        return true
    else:
        return false
""")
bundle = package(positive)
report = correspond(bundle, positive, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert {entry["name"]: entry["status"] for entry in report["functions"]} == {
    "truth": "checked", "caller": "checked"
}, report

changed = write("changed", positive.read_text().replace("ensure result == true", "ensure result == false", 1).replace("            return true", "            return false", 1))
report = correspond(bundle, changed, 1)
assert report["package"]["status"] == "replayed" and report["source_admissible"] is True, report
assert {entry["name"]: (entry["status"], entry["reason"]) for entry in report["functions"]} == {
    "truth": ("unmatched", "unproved-obligation"),
    "caller": ("unsupported", "callee-unchecked"),
}, report

unchecked = write("unchecked", positive.read_text().replace("            ensure result == true\n", "", 1))
report = correspond(bundle, unchecked, 1)
assert report["package"]["status"] == "replayed" and report["source_admissible"] is True, report
assert {entry["name"]: (entry["status"], entry["reason"]) for entry in report["functions"]}["caller"] == (
    "unmatched", "unproved-obligation"
), report

wrong_owner = write("wrong_owner", positive.read_text().replace(
    "if HelperPolicy::truth(value):", "if OtherPolicy::truth(value):") + """

module OtherPolicy:
    public:
        def truth(value: i64) -> bool:
            requires value >= 0
            ensure result == true
            return true
""")
report = correspond(bundle, wrong_owner, 1)
assert report["package"]["status"] == "replayed" and report["source_admissible"] is True, report
owner_statuses = {(tuple(entry["owner"]), entry["name"]): (entry["status"], entry["reason"])
                  for entry in report["functions"]}
assert owner_statuses[((), "caller")] == ("unsupported", "callee-unchecked"), report
assert owner_statuses[(("OtherPolicy",), "truth")][0] != "checked", report

print("branch-condition helper calls match checked source summaries; changed summaries and unchecked facts refuse")
