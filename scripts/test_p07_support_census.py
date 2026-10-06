#!/usr/bin/env python3
"""Unit checks for bounded P-07 report admission and failure capture."""
import tempfile
import json
from pathlib import Path
import subprocess
import sys

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
incomplete = report(certificates=2, replayed=1, gaps=1)
partial = census.partial_report_metadata(incomplete)
assert partial["status"] == "proved" and partial["replay"] == incomplete["replay"]
assert partial["summary"] == incomplete["summary"]
kind_ranking = census.rank_unsupported_kinds([
    {"input": "a", "error": None, "unsupported_sites": ["src:1 f function-summary-unverified",
                                                               "src:2 g control-flow-analysis-budget"]},
    {"input": "b", "error": None, "unsupported_sites": ["src:3 h function-summary-unverified"]},
    {"input": "c", "error": "incomplete-replay", "unsupported_sites": ["src:4 i fake-kind"]},
])
assert kind_ranking[0] == {
    "kind": "function-summary-unverified", "site_count": 2,
    "affected_inputs": ["a", "b"], "input_count": 2,
}, kind_ranking
assert all(item["kind"] != "fake-kind" for item in kind_ranking)

original_killpg = census.os.killpg
try:
    census.os.killpg = lambda *_: (_ for _ in ()).throw(PermissionError("simulated exit race"))
    exited = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    exited.wait()
    census.terminate_process_group(exited)

    live = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(10)"], start_new_session=True
    )
    census.terminate_process_group(live)
    assert live.wait() != 0, "EPERM fallback did not terminate the direct child"
finally:
    census.os.killpg = original_killpg

with tempfile.TemporaryDirectory(prefix="elisa-p07-unit-") as directory:
    temp = Path(directory)
    source = temp / "input.elisa"
    source.write_text("proof input\n")
    executable = temp / "fake-proof"
    executable.write_text("#!/bin/sh\nprintf 'not-json\\n'\nexit 1\n")
    executable.chmod(0o755)
    original_binary = census.BINARY
    original_output_limit = census.MAX_OUTPUT_BYTES
    census.BINARY = executable
    try:
        invalid = census.run(source, timeout=5, rss_limit_kib=100_000)
        assert invalid["error"] == "invalid-json", invalid
        assert invalid["exit_code"] == 1, invalid
        valid_report = json.dumps(report())
        executable.write_text(
            "#!/usr/bin/env python3\nimport sys\nprint(" + repr(valid_report) +
            ")\nsys.stdout.write(' ' * 100000)\n", encoding="utf-8")
        executable.chmod(0o755)
        large = census.run(source, timeout=5, rss_limit_kib=100_000)
        assert large["error"] is None and large["stdout_bytes"] > 65536, large
        census.MAX_OUTPUT_BYTES = 1024
        output_limited = census.run(source, timeout=5, rss_limit_kib=100_000)
        assert output_limited["error"] == "output-limit", output_limited
        census.MAX_OUTPUT_BYTES = original_output_limit
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
        census.MAX_OUTPUT_BYTES = original_output_limit

print("P-07 census: pipe-volume, output, status/exit, replay, JSON, timeout and RSS gates passed")
