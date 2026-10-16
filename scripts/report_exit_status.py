#!/usr/bin/env python3
"""Validate a proof JSON report's stable top-level verdict and map it to a process exit."""

import json
from pathlib import Path
import sys


def _reject_nonstandard_constant(value):
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def _reject_unpaired_surrogates(value):
    pending = [iter((value,))]
    while pending:
        try:
            item = next(pending[-1])
        except StopIteration:
            pending.pop()
            continue
        if isinstance(item, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                raise ValueError("JSON string contains an unpaired surrogate")
        elif isinstance(item, dict):
            pending.append(iter(component for pair in item.items() for component in pair))
        elif isinstance(item, list):
            pending.append(iter(item))


def expected_exit(report):
    _reject_unpaired_surrogates(report)
    return _expected_exit_validated(report)


def _expected_exit_validated(report):
    if not isinstance(report, dict):
        raise ValueError("JSON report root must be an object")
    status = report.get("status")
    if status == "proved":
        if report.get("verification_state") != "proved":
            raise ValueError("proved status requires verification_state=proved")
        summary = report.get("summary")
        replay = report.get("replay")
        if not isinstance(summary, dict):
            raise ValueError("proved status requires obligation counters")
        proven, obligations = summary.get("proven"), summary.get("obligations")
        if (type(proven) is not int or type(obligations) is not int or proven < 0
                or obligations < proven or proven != obligations):
            raise ValueError("proved status requires all obligations counted as proven")
        gaps = replay.get("gaps") if isinstance(replay, dict) else None
        if type(gaps) is not int or gaps != 0:
            raise ValueError("proved status requires a replay report with zero gaps")
        return 0
    if status == "failed":
        # JSON values may be arrays or objects, which are unhashable in Python. Use
        # tuple membership so malformed states produce the same validation error
        # instead of leaking a TypeError from the reference CLI.
        if report.get("verification_state") not in ("unknown", "unsupported", "disproved"):
            raise ValueError("failed status requires unknown, unsupported, or disproved verification_state")
        return 1
    if status == "proved_with_replay_gaps":
        replay = report.get("replay")
        gaps = replay.get("gaps") if isinstance(replay, dict) else None
        if report.get("verification_state") != "unknown" or type(gaps) is not int or gaps <= 0:
            raise ValueError("proved_with_replay_gaps requires unknown state and positive replay.gaps")
        return 1
    raise ValueError(f"unrecognized top-level result-lattice status: {status!r}")


def main(argv):
    if len(argv) != 2:
        print("usage: report_exit_status.py <report.json>", file=sys.stderr)
        return 2
    try:
        report = json.loads(
            Path(argv[1]).read_text(encoding="utf-8"),
            parse_constant=_reject_nonstandard_constant,
        )
        _reject_unpaired_surrogates(report)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"malformed --json output: {error}", file=sys.stderr)
        return 2
    try:
        print(_expected_exit_validated(report))
        return 0
    except ValueError as error:
        print(f"invalid --json result lattice: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
