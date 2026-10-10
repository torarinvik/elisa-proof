"""Module and scoped function collection keeps complete owner paths collision-safe."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(os.environ.get("ELISA_PROOF_CONTROL_DIR", tempfile.mkdtemp(prefix="elisa-proof-module-owners-")))
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


def correspond(bundle, source):
    run = subprocess.run([str(BINARY), "--correspondence", str(bundle), str(source)],
                         capture_output=True, text=True, timeout=300)
    (WORK / f"{source.stem}.correspondence.stdout").write_text(run.stdout)
    (WORK / f"{source.stem}.correspondence.stderr").write_text(run.stderr)
    (WORK / f"{source.stem}.correspondence.exit").write_text(f"{run.returncode}\n")
    assert run.returncode in (0, 1), (run.returncode, run.stdout[-1000:], run.stderr[-400:])
    return json.loads(run.stdout)


source_text = """module First:
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
source = write("nested_modules", source_text)
bundle = package(source)
report = correspond(bundle, source)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert [(item["owner"], item["name"], item["status"]) for item in report["functions"]] == [
    (["First", "Inner"], "positive", "checked"),
    (["Second"], "positive", "checked"),
], report

# A fully qualified declaration path is retained as parsed; it is not appended to the lexical
# parent or flattened to the shared leaf name.
changed_path = write("qualified_path", source_text.replace(
    "    module Inner:", "    module Other::Inner:"))
changed_report = correspond(bundle, changed_path)
assert changed_report["source_admissible"] is True and changed_report["package"]["status"] == "replayed", changed_report
assert [(item["owner"], item["name"], item["status"]) for item in changed_report["functions"]] == [
    (["Other", "Inner"], "positive", "checked"),
    (["Second"], "positive", "checked"),
], changed_report

# Two declarations with the same complete module path and leaf are ambiguous, even though the
# original package replays. The correspondence collector must refuse the source inventory.
duplicate_path = write("duplicate_owner", source_text.replace(
    "module Second:",
    "module First::Inner:\n    public:\n        def positive(value: i64) -> bool:\n            ensure result == (value > 0)\n            return value > 0\n\nmodule Second:"))
duplicate_report = correspond(bundle, duplicate_path)
assert duplicate_report["package"]["status"] == "replayed", duplicate_report
assert duplicate_report["source_admissible"] is False or duplicate_report["summary"]["coverage"] != "complete", duplicate_report

print("nested/scoped owner paths remain exact; same-leaf modules stay distinct and duplicate owners refuse")
