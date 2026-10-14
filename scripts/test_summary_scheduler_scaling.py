"""Large schedules and finding-heavy reports stay within the source-work bound."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from qualified_test_binary import proof_test_binary


ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)


def check(source: str, expected_kind: str, expected_count: int) -> None:
    with tempfile.TemporaryDirectory(prefix="elisa-summary-schedule-") as temporary:
        source_path = Path(temporary) / "schedule.elisa"
        source_path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [str(BINARY), "--json", str(source_path)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    report = json.loads(result.stdout)
    assert result.returncode == 0, (result.returncode, result.stderr[-2000:], report)
    assert report["status"] == report["verification_state"] == "proved", report["status"]
    assert not any(finding["kind"] == "resource-analysis-budget" for finding in report["findings"]), report["findings"]
    declarations = [
        declaration
        for declaration in report["declaration_details"]
        if declaration.get("kind") == expected_kind
    ]
    assert len(declarations) == expected_count, (expected_kind, len(declarations))
    assert all(declaration["verified"] for declaration in declarations), declarations
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]


FUNCTION_COUNT = 112
function_lines: list[str] = []
for index in range(FUNCTION_COUNT):
    function_lines.append(f"def scheduler_function_{index:03}(value: i64) -> i64:")
    if index + 1 < FUNCTION_COUNT:
        callee = f"scheduler_function_{index + 1:03}(value)"
        function_lines.append("    ensure result == 0")
        # The repeated edge stresses multiplicity while subtraction avoids overflow.
        function_lines.append(f"    return {callee} - {callee}")
    else:
        function_lines.extend(("    ensure result == value", "    return value"))
    function_lines.append("")
check("\n".join(function_lines), "function", FUNCTION_COUNT)

LEMMA_COUNT = 112
lemma_lines: list[str] = []
for index in range(LEMMA_COUNT):
    lemma_lines.extend(
        (
            f"lemma scheduler_lemma_{index:03}(value: i64):",
            "    requires value >= 0",
            "    ensure value >= 0",
        )
    )
    if index + 1 < LEMMA_COUNT:
        # Reverse declaration order prevents a readiness scan from finding the next
        # dependency immediately; every edge remains acyclic.
        lemma_lines.append(f"    scheduler_lemma_{index + 1:03}(value)")
    lemma_lines.append("")
ISOLATED_LEMMA_COUNT = 128
for index in range(ISOLATED_LEMMA_COUNT):
    lemma_lines.extend(
        (
            f"lemma scheduler_isolated_lemma_{index:03}(value: i64):",
            "    requires value >= 0",
            "    ensure value >= 0",
            "",
        )
    )
check("\n".join(lemma_lines), "lemma", LEMMA_COUNT + ISOLATED_LEMMA_COUNT)

FINDING_COUNT = 512
negative_lines: list[str] = []
for index in range(FINDING_COUNT):
    negative_lines.extend(
        (
            f"def scheduler_finding_{index:03}(value: i64) -> i64:",
            "    ensure result == value + 1",
            "    return value",
            "",
        )
    )
with tempfile.TemporaryDirectory(prefix="elisa-summary-findings-") as temporary:
    source_path = Path(temporary) / "finding-heavy.elisa"
    source_path.write_text("\n".join(negative_lines), encoding="utf-8")
    result = subprocess.run(
        [str(BINARY), "--json", str(source_path)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
report = json.loads(result.stdout)
assert result.returncode == 1 and report["status"] == "failed", report
assert not any(finding["kind"] == "resource-analysis-budget" for finding in report["findings"]), report["findings"]
assert sum(finding["kind"] == "ensure-unproven" for finding in report["findings"]) >= FINDING_COUNT, report["findings"]
assert report["replay"]["gaps"] == 0, report["replay"]

# Keep leaf names identical across modules to stress source identity indexing under ambiguous
# declaration names. The source guard also requires ownerless findings to update the bounded
# per-name summary without walking this duplicate chain.
DUPLICATE_NAME_COUNT = 512
duplicate_name_lines: list[str] = []
for index in range(DUPLICATE_NAME_COUNT):
    duplicate_name_lines.extend(
        (
            f"module scheduler_duplicate_scope_{index:03}:",
            "    def repeated_finding_name(value: i64) -> i64:",
            "        ensure result == value + 1",
            "        return value",
            "",
        )
    )
with tempfile.TemporaryDirectory(prefix="elisa-summary-duplicate-findings-") as temporary:
    source_path = Path(temporary) / "duplicate-finding-heavy.elisa"
    source_path.write_text("\n".join(duplicate_name_lines), encoding="utf-8")
    result = subprocess.run(
        [str(BINARY), "--json", str(source_path)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
duplicate_report = json.loads(result.stdout)
assert result.returncode == 1 and duplicate_report["status"] == "failed", duplicate_report
assert not any(
    finding["kind"] == "resource-analysis-budget" for finding in duplicate_report["findings"]
), duplicate_report["findings"]
duplicate_failures = [
    finding for finding in duplicate_report["findings"]
    if finding["kind"] == "ensure-unproven"
]
assert len(duplicate_failures) == DUPLICATE_NAME_COUNT, duplicate_failures
assert len({finding["line"] for finding in duplicate_failures}) == DUPLICATE_NAME_COUNT, duplicate_failures
assert duplicate_report["replay"]["gaps"] == 0, duplicate_report["replay"]

print("summary scheduling: reverse chains, isolated lemmas, unique and duplicate-name finding scales checked")
