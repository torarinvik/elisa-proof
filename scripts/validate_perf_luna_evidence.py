#!/usr/bin/env python3
"""Validate a paired benchmark report without rerunning the measured workload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from perf_luna_evidence_validation import validate_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="paired benchmark JSON report")
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        result = validate_report(report)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError) as error:
        print(f"benchmark evidence invalid: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
