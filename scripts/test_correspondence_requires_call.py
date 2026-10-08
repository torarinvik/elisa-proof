"""Requires-call summaries need a unique checked total-pure source owner."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(os.environ.get("ELISA_PROOF_CONTROL_DIR", tempfile.mkdtemp(prefix="elisa-proof-requires-call-")))
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
    assert run.returncode in (0, 1), (run.returncode, run.stdout[-1000:], run.stderr[-400:])
    path = WORK / f"{source.stem}.package.json"
    path.write_text(run.stdout)
    return path


def correspond(bundle, source):
    run = subprocess.run([str(BINARY), "--correspondence", str(bundle), str(source)],
                         capture_output=True, text=True, timeout=300)
    (WORK / f"{source.stem}.correspondence.stdout").write_text(run.stdout)
    (WORK / f"{source.stem}.correspondence.stderr").write_text(run.stderr)
    (WORK / f"{source.stem}.correspondence.exit").write_text(f"{run.returncode}\n")
    assert run.returncode in (0, 1), (run.returncode, run.stdout[-1200:], run.stderr[-400:])
    return json.loads(run.stdout)


def function(report, name):
    return next(item for item in report["functions"] if item["name"] == name)


positive_text = """module BoundedPathPolicy:
    public:
        def admitted(length: i64, capacity: i64) -> bool:
            ensure result == (capacity > 0 and length >= 0 and length < capacity)
            return capacity > 0 and length >= 0 and length < capacity

        def nonempty_admitted(length: i64, capacity: i64) -> bool:
            ensure result == (capacity > 0 and length > 0 and length < capacity)
            return capacity > 0 and length > 0 and length < capacity

module BoundedPathPolicyLaws:
    public:
        def retained_take_copy_bounds(length: i64, capacity: i64) -> bool:
            requires BoundedPathPolicy::nonempty_admitted(length, capacity)
            ensure result
            return length >= 1 and length < capacity

        def empty_take_refused(capacity: i64) -> bool:
            ensure result == false
            return BoundedPathPolicy::nonempty_admitted(0, capacity)
"""
positive = write("positive", positive_text)
positive_bundle = package(positive)
positive_report = correspond(positive_bundle, positive)
assert positive_report["source_admissible"] is True and positive_report["package"]["status"] == "replayed", positive_report
assert function(positive_report, "nonempty_admitted")["status"] == "checked", positive_report
assert function(positive_report, "retained_take_copy_bounds")["status"] == "checked", positive_report
assert function(positive_report, "empty_take_refused")["status"] == "checked", positive_report

# A different owner with the same leaf name cannot stand in for the package's exact callee.
wrong_owner = write("wrong_owner", positive_text.replace(
    "module BoundedPathPolicyLaws:",
    "module OtherPolicy:\n    public:\n        def nonempty_admitted(length: i64, capacity: i64) -> bool:\n            ensure result == false\n            return false\n\nmodule BoundedPathPolicyLaws:").replace(
    "requires BoundedPathPolicy::nonempty_admitted(length, capacity)",
    "requires OtherPolicy::nonempty_admitted(length, capacity)"))
wrong_owner_report = correspond(positive_bundle, wrong_owner)
assert wrong_owner_report["source_admissible"] is True, wrong_owner_report
assert function(wrong_owner_report, "retained_take_copy_bounds")["status"] != "checked", wrong_owner_report

# A changed callee and changed actual arguments also fail to match the original source theorem.
changed_callee = write("changed_callee", positive_text.replace(
    "requires BoundedPathPolicy::nonempty_admitted(length, capacity)",
    "requires BoundedPathPolicy::admitted(length, capacity)"))
changed_callee_report = correspond(positive_bundle, changed_callee)
assert function(changed_callee_report, "retained_take_copy_bounds")["status"] != "checked", changed_callee_report

changed_arguments = write("changed_arguments", positive_text.replace(
    "requires BoundedPathPolicy::nonempty_admitted(length, capacity)",
    "requires BoundedPathPolicy::nonempty_admitted(capacity, length)"))
changed_arguments_report = correspond(positive_bundle, changed_arguments)
assert function(changed_arguments_report, "retained_take_copy_bounds")["status"] != "checked", changed_arguments_report

# The callee's own requires must be supplied by earlier caller facts. The guarded caller checks;
# its copy without the explicit capacity premise does not.
precondition_text = """module CheckedPolicy:
    public:
        def positive(value: i64) -> bool:
            requires value > 0
            ensure result == (value > 0)
            return value > 0

module CallerPolicy:
    public:
        def guarded(value: i64) -> bool:
            requires value > 0
            requires CheckedPolicy::positive(value)
            ensure result
            return value > 0
"""
guarded = write("guarded_precondition", precondition_text)
guarded_bundle = package(guarded)
guarded_report = correspond(guarded_bundle, guarded)
assert function(guarded_report, "positive")["status"] == "checked", guarded_report
assert function(guarded_report, "guarded")["status"] == "checked", guarded_report

missing = write("missing_precondition", precondition_text.replace(
    "            requires value > 0\n            requires CheckedPolicy::positive(value)",
    "            requires CheckedPolicy::positive(value)"))
missing_bundle = package(missing)
missing_report = correspond(missing_bundle, missing)
assert missing_report["source_admissible"] is True, missing_report
assert function(missing_report, "guarded")["status"] != "checked", missing_report

# A checked bool body without a checked postcondition, or with a late requires clause, is not
# eligible as a caller summary. The latter ordering would otherwise make call evaluation omit
# a source precondition that the function walker had already consumed as an ensure.
no_ensure_text = precondition_text.replace(
    "            ensure result == (value > 0)\n", "")
no_ensure = write("no_ensure", no_ensure_text)
no_ensure_bundle = package(no_ensure)
no_ensure_report = correspond(no_ensure_bundle, no_ensure)
assert function(no_ensure_report, "positive")["status"] == "checked", no_ensure_report
assert function(no_ensure_report, "guarded")["status"] != "checked", no_ensure_report

late_requires_text = precondition_text.replace(
    "            requires value > 0\n            ensure result == (value > 0)",
    "            ensure result == (value > 0)\n            requires value > 0")
late_requires = write("late_requires", late_requires_text)
late_requires_bundle = package(late_requires)
late_requires_report = correspond(late_requires_bundle, late_requires)
assert function(late_requires_report, "guarded")["status"] != "checked", late_requires_report

print("requires-call checked-summary positive, owner/callee/argument mismatch, missing-precondition, and malformed-summary controls pass")

# Nested owners with the same leaf function name remain distinct. A same-leaf helper in another
# module has a stronger precondition, so resolving the wrong owner cannot check the caller.
owner_text = """module First:
    module Inner:
        public:
            def positive(value: i64) -> bool:
                ensure result == (value > 0)
                return value > 0

module Second:
    public:
        def positive(value: i64) -> bool:
            ensure result == (value > 0)
            return value > 0
"""
owner_source = write("nested_owner_positive", owner_text)
owner_bundle = package(owner_source)
owner_report = correspond(owner_bundle, owner_source)
assert owner_report["source_admissible"] is True and owner_report["package"]["status"] == "replayed", owner_report
assert [(item["owner"], item["name"], item["status"]) for item in owner_report["functions"]] == [
    (["First", "Inner"], "positive", "checked"),
    (["Second"], "positive", "checked"),
], owner_report

wrong_nested_owner = write("nested_owner_wrong_leaf", owner_text.replace(
    "    module Inner:", "    module Other::Inner:"))
wrong_nested_report = correspond(owner_bundle, wrong_nested_owner)
assert wrong_nested_report["source_admissible"] is True and wrong_nested_report["package"]["status"] == "replayed", wrong_nested_report
assert wrong_nested_report["summary"]["coverage"] == "complete", wrong_nested_report
assert [(item["owner"], item["name"]) for item in wrong_nested_report["functions"]] == [
    (["Other", "Inner"], "positive"), (["Second"], "positive")
], wrong_nested_report

# Reopening the same module path creates an ambiguous owner overload set; the collector must not
# flatten or silently select the first declaration.
same_owner_duplicate = write("same_owner_duplicate", owner_text.replace(
    "module Second:",
    "module First::Inner:\n    public:\n        def positive(value: i64) -> bool:\n            requires value > 0\n            ensure result == (value > 0)\n            return value > 0\n\nmodule Second:"))
duplicate_report = correspond(owner_bundle, same_owner_duplicate)
assert duplicate_report["package"]["status"] == "replayed", duplicate_report
assert duplicate_report["source_admissible"] is False or duplicate_report["summary"]["coverage"] != "complete", duplicate_report
