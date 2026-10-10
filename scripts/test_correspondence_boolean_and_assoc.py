"""Expanding a checked Boolean helper preserves conjunction order and source identity."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(os.environ.get("ELISA_PROOF_CONTROL_DIR", tempfile.mkdtemp(prefix="elisa-proof-and-assoc-")))
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

direct_positive = write("direct_positive", """module HelperPolicy:
    public:
        def combine(second: bool, third: bool) -> bool:
            ensure result == (second and third)
            return second and third

def caller(second: bool, third: bool) -> bool:
    ensure result == (second and third)
    return HelperPolicy::combine(second, third)
""")
direct_bundle = package(direct_positive)
report = correspond(direct_bundle, direct_positive, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert [(item["owner"], item["name"], item["status"]) for item in report["functions"]] == [
    (["HelperPolicy"], "combine", "checked"), ([], "caller", "checked")
], report

direct_expansion = write("direct_expansion", """module HelperPolicy:
    public:
        def combine(second: bool, third: bool) -> bool:
            ensure result == (second and third)
            return second and third

def caller(second: bool, third: bool) -> bool:
    ensure result == ((second and third) and third)
    return HelperPolicy::combine(second, third) and third
""")
direct_expansion_bundle = package(direct_expansion)
report = correspond(direct_expansion_bundle, direct_expansion, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert [(item["owner"], item["name"], item["status"]) for item in report["functions"]] == [
    (["HelperPolicy"], "combine", "checked"), ([], "caller", "checked")
], report

or_positive = write("or_positive", positive.read_text().replace(
    "ensure result == (first and second and third)",
    "ensure result == ((not first) or (second and third))").replace(
    "return first and HelperPolicy::combine(second, third)",
    "return (not first) or HelperPolicy::combine(second, third)"))
or_bundle = package(or_positive)
report = correspond(or_bundle, or_positive, 0)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert [(item["owner"], item["name"], item["status"]) for item in report["functions"]] == [
    (["HelperPolicy"], "combine", "checked"), ([], "caller", "checked")
], report

# A helper summary is valid only on the branch where the source actually evaluates the call.
wrong_guard = write("wrong_guard", positive.read_text().replace(
    "return first and HelperPolicy::combine(second, third)",
    "return (not first) and HelperPolicy::combine(second, third)"))
wrong_guard_bundle = package(wrong_guard)
report = correspond(wrong_guard_bundle, wrong_guard, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
caller = next(item for item in report["functions"] if item["name"] == "caller")
assert caller["status"] != "checked", report

# A helper's caller-side requires obligation remains branch-specific and must replay separately.
missing_precondition = write("missing_precondition", positive.read_text().replace(
    "ensure result == (second and third)",
    "requires second\n            ensure result == (second and third)", 1))
missing_bundle = package(missing_precondition)
report = correspond(missing_bundle, missing_precondition, 1)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
caller = next(item for item in report["functions"] if item["name"] == "caller")
assert caller["status"] != "checked", report

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

reordered_operands = write("reordered_operands", positive.read_text().replace(
    "first and HelperPolicy::combine(second, third)",
    "second and first and HelperPolicy::combine(second, third)"))
report = correspond(bundle, reordered_operands, 1)
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
