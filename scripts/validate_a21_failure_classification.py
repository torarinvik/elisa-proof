#!/usr/bin/env python3
"""Validate the immutable A21 failure-classification ledger and optional source log."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/evidence/2026-10-06-a21-failure-classification.md"
LEDGER = ROOT / "docs/evidence/2026-10-06-a21-failure-events.tsv"
LOG_SHA256 = "412d9be68c3a0b2c496a21a938455d1033459fab0f9a706896133b7e7a2de913"
EXPECTED_MARKERS = (
    2,
    19,
    39,
    45,
    72,
    79,
    85,
    94,
    105,
    121,
    127,
    136,
    141,
    146,
    151,
    163,
    178,
    180,
    195,
    202,
    210,
    216,
    224,
    237,
    261,
    267,
    272,
    280,
    291,
    303,
    308,
    315,
    327,
    342,
    347,
    352,
    357,
    372,
    377,
    392,
    407,
    422,
    437,
    452,
    467,
    482,
    487,
    502,
    507,
    512,
    526,
    528,
    534,
    549,
    564,
    579,
    584,
    599,
    604,
    619,
    624,
    628,
    630,
    674,
    676,
    678,
    680,
    682,
    684,
    686,
    688,
    703,
    705,
    710,
    715,
    720,
    725,
    730,
    735,
    740,
    745,
    750,
    755,
    760,
    765,
    771,
    776,
    791,
    796,
    801,
    806,
    821,
    836,
    841,
    858,
    863,
    868,
    883,
    898,
    913,
    918,
    933,
    948,
    953,
    968,
    983,
    998,
    1003,
    1018,
    1023,
    1038,
    1053,
    1068,
    1083,
    1088,
    1093,
    1108,
    1123,
    1128,
    1143,
    1158,
    1173,
    1178,
    1193,
    1198,
    1213,
    1218,
    1223,
    1228,
    1233,
    1235,
    1240,
    1245,
    1252,
    1267,
    1272,
    1274,
    1675
)
EXPECTED_CLASSES = {
    "REPLAY": 97,
    "OPEN": 3,
    "COVERAGE": 9,
    "SEMANTIC": 3,
    "EXPECTATION": 12,
    "TOOL": 4,
    "AGGREGATE": 5,
    "CLI-CASCADE": 4,
    "CENSUS": 1,
}
EXPECTED_MARKERS_BY_KIND = {"command": 34, "step": 104}


def validate(log_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    try:
        report = REPORT.read_text(encoding="utf-8")
        with LEDGER.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    except OSError as exc:
        return [f"cannot read evidence artifacts: {exc}"]

    for required in (
        "f2d375704887a0ca0603b085d633cf22b03b8b4d",
        "461fdbadf130de93ea588f5b0fc07ddb773dcf6a89b247d3af0a9434b51316f8",
        LOG_SHA256,
        "113765d13774d86225efba5aae6d9e18de2cabfc3e121036f27b35ca3da4eea8",
        "8e941cc6d183fc4791ed0dd433c5bf8d782f78584f8b01f5e24607da793cd832",
        "65a9308c53b510365aa69644a0bcaa9a071ea2006683dad6bf2ec12fc394f6b3",
        "This is a historical result for one identified test run, not a current-HEAD result",
        "no claim about current HEAD",
    ):
        if required not in report:
            errors.append(f"report is missing pinned identity/scope text: {required}")

    expected_columns = {"log_line", "marker", "source_line", "class", "failure_signal"}
    if not rows or set(rows[0]) != expected_columns:
        return errors + ["event ledger header/schema mismatch"]

    parsed_lines: list[int] = []
    marker_kinds: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    allowed_classes = set(EXPECTED_CLASSES)
    for row_number, row in enumerate(rows, start=2):
        try:
            log_line = int(row["log_line"])
        except (TypeError, ValueError):
            errors.append(f"ledger row {row_number}: invalid log line")
            continue
        parsed_lines.append(log_line)
        if row["marker"] not in EXPECTED_MARKERS_BY_KIND:
            errors.append(f"ledger row {row_number}: invalid marker kind {row['marker']!r}")
        else:
            marker_kinds[row["marker"]] += 1
        if row["class"] not in allowed_classes:
            errors.append(f"ledger row {row_number}: invalid classification {row['class']!r}")
        else:
            class_counts[row["class"]] += 1
        if not row["source_line"].isdigit() or not row["failure_signal"].strip():
            errors.append(f"ledger row {row_number}: missing source line or assertion signal")

    if tuple(parsed_lines) != EXPECTED_MARKERS:
        errors.append("event ledger does not contain the exact ordered 138-marker snapshot census")
    if len(set(parsed_lines)) != len(parsed_lines):
        errors.append("event ledger repeats a full-test-log marker")
    if marker_kinds != Counter(EXPECTED_MARKERS_BY_KIND):
        errors.append(f"marker-kind counts differ: {dict(marker_kinds)}")
    if class_counts != Counter(EXPECTED_CLASSES):
        errors.append(f"classification counts differ: {dict(class_counts)}")
    report_counts = {
        name: int(count)
        for name, count in re.findall(
            r"^\|\s*([A-Z][A-Z-]*)\s*\|\s*(\d+)\s*\|",
            report,
            flags=re.MULTILINE,
        )
    }
    if report_counts != EXPECTED_CLASSES:
        errors.append(f"report classification totals differ: {report_counts}")

    if log_path is not None:
        try:
            log_bytes = log_path.read_bytes()
        except OSError as exc:
            return errors + [f"cannot read supplied immutable log: {exc}"]
        observed_sha = hashlib.sha256(log_bytes).hexdigest()
        if observed_sha != LOG_SHA256:
            errors.append(f"supplied log SHA-256 mismatch: {observed_sha}")
        observed: list[tuple[int, str, str]] = []
        for line_number, line in enumerate(log_bytes.decode("utf-8").splitlines(), start=1):
            if not line.startswith("KEEP_GOING:"):
                continue
            kind = "command" if "command failed" in line else "step"
            match = re.search(r"at line (\d+)", line)
            source_line = match.group(1) if match else "?"
            observed.append((line_number, kind, source_line))
        expected = [
            (int(row["log_line"]), row["marker"], row["source_line"])
            for row in rows
        ]
        if observed != expected:
            errors.append("ledger markers/source lines do not match the supplied full-test log")
        if not log_bytes.decode("utf-8").rstrip().endswith(
            "proof test matrix failed: 138 step(s) failed (KEEP_GOING)"
        ):
            errors.append("supplied log does not end with the recorded 138-failure summary")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, help="optionally verify against the original full-suite log")
    args = parser.parse_args()
    errors = validate(args.log)
    if errors:
        for error in errors:
            print(f"A21 classification invalid: {error}")
        return 1
    print("A21 classification valid: 138 exact snapshot failure markers, identities and totals agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
