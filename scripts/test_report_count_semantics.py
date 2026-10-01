"""The JSON summary distinguishes unresolved obligations from finding records."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "build/elisa-proof"


def run(name):
    result = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / name)],
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    expected_exit = 0 if report["status"] == "proved" else 1
    assert result.returncode == expected_exit, (name, result.returncode, report["status"])
    summary = report["summary"]
    assert summary["unproven"] == summary["obligations"] - summary["proven"], summary
    assert summary["finding_count"] == len(report["findings"]), summary
    assert summary["failed"] == summary["finding_count"], summary
    return report


proved = run("verified.elisa")
assert proved["summary"]["unproven"] == 0
assert proved["summary"]["finding_count"] == 0

# This fixture has one non-goal diagnostic in addition to its failed obligations. It guards
# against clients treating the legacy `failed` finding count as obligations minus `proven`.
rejected = run("rejected_unsigned_local_states.elisa")
assert rejected["summary"]["unproven"] == 16
assert rejected["summary"]["finding_count"] == 17
assert rejected["summary"]["finding_count"] > rejected["summary"]["unproven"]
text_result = subprocess.run(
    [str(BINARY), str(ROOT / "examples/rejected_unsigned_local_states.elisa")],
    capture_output=True,
    text=True,
)
assert text_result.returncode == 1
assert "  unproven: 16\n" in text_result.stdout
assert "  findings: 17\n" in text_result.stdout
assert "  failed:" not in text_result.stdout

print("report counts: unproven obligations and finding records are distinct and consistent")
