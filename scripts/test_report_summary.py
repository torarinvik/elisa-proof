#!/usr/bin/env python3
"""Compare the compact report with the authoritative full JSON report."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(flag: str, fixture: str):
    completed = subprocess.run(
        [str(BINARY), flag, str(ROOT / "examples" / fixture)],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def compare(fixture: str, expected_status: str):
    full_code, full = report("--json", fixture)
    compact_code, compact = report("--summary-json", fixture)
    assert full["status"] == compact["status"] == expected_status
    assert full["verification_state"] == compact["verification_state"]
    assert full["engine_state"] == compact["engine_state"]
    assert full["source"] == compact["source"]
    assert full["trust"]["trusted_assumptions"] == compact["trust"]["trusted_assumptions"]
    for key in (
        "declarations", "obligations", "proven", "unproven", "failed",
        "finding_count", "semantic_diagnostics", "semantic_errors",
    ):
        if key in full["summary"]:
            assert compact["summary"][key] == full["summary"][key], key
    for status in ("disproved", "unsupported", "unknown"):
        count_key = f"{status}_findings"
        assert compact["summary"][count_key] == sum(
            finding.get("status") == status for finding in full["findings"]
        ), count_key
    assert compact["trust"]["trusted_boundary_facts"] == full["trust"]["trusted_boundary_facts"]
    assert compact["trust"]["kernel_replayed_certificates"] == full["trust"]["kernel_replayed_certificates"]
    assert compact["details"] == {
        "omitted": True,
        "authoritative_route": "elisa-proof --json <file.elisa>",
    }
    assert len(json.dumps(compact)) < len(json.dumps(full))
    assert (compact_code == 0) == (full_code == 0)


compare("loop_invariants_compile.elisa", "proved")
compare("rejected.elisa", "failed")
print("compact/full report conclusions and authoritative counts agree")
