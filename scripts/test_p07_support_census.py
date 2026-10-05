#!/usr/bin/env python3
"""Unit checks for bounded P-07 report admission and failure capture."""
import tempfile
from pathlib import Path

import p07_support_census as census


def report(status="proved", certificates=2, replayed=2, gaps=0):
    return {
        "status": status,
        "summary": {"proven": 2 if status == "proved" else 1, "obligations": 2},
        "replay": {"certificates": certificates, "replayed": replayed, "gaps": gaps},
        "declaration_details": [],
        "findings": [],
    }


assert census.validate_report(report(), 0) is None
assert census.validate_report(report("failed"), 1) is None
assert census.validate_report(report(), 1).startswith("status-exit-mismatch")
assert census.validate_report(report(certificates=2, replayed=1), 0) == "incomplete-replay"
assert census.validate_report(report(gaps=1), 0) == "incomplete-replay"
assert census.validate_report({"summary": {}}, 0) == "incomplete-report"
assert census.validate_report(report("unknown"), 1).startswith("unknown-status")

with tempfile.TemporaryDirectory(prefix="elisa-p07-unit-") as directory:
    temp = Path(directory)
    source = temp / "input.elisa"
    source.write_text("proof input\n")
    executable = temp / "fake-proof"
    executable.write_text("#!/bin/sh\nprintf 'not-json\\n'\nexit 1\n")
    executable.chmod(0o755)
    original_binary = census.BINARY
    census.BINARY = executable
    try:
        invalid = census.run(source, timeout=5, rss_limit_kib=100_000)
        assert invalid["error"] == "invalid-json", invalid
        assert invalid["exit_code"] == 1, invalid
        executable.write_text("#!/bin/sh\nsleep 3\n")
        executable.chmod(0o755)
        timed_out = census.run(source, timeout=1, rss_limit_kib=100_000)
        assert timed_out["error"] == "timeout", timed_out
        executable.write_text("#!/bin/sh\nsleep 3\n")
        executable.chmod(0o755)
        rss_limited = census.run(source, timeout=5, rss_limit_kib=1)
        assert rss_limited["error"] == "rss-limit", rss_limited
    finally:
        census.BINARY = original_binary

print("P-07 census: status/exit, replay completeness, invalid JSON, timeout, and RSS gates passed")
