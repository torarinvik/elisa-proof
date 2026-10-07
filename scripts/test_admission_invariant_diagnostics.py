"""Admission accounting failures stay distinct from ordinary open proof goals."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
for name, expected_exit, expected_reason in (
        ("source_context_scope", 0, ""),
        ("tactic_repair_target", 1, ""),
        ("contract_placement", 0, ""),
        ("condition_call_positions", 1, "goal-attempt-coverage")):
    for route in ("--json", "--summary-json"):
        result = subprocess.run([BINARY, route, str(ROOT / "examples" / (name + ".elisa"))],
                                capture_output=True, text=True, timeout=60)
        report = json.loads(result.stdout)
        assert result.returncode == expected_exit, (name, route, report["status"])
        assert report["admission_invariant_failure"] == expected_reason, (name, route)
        if name == "contract_placement":
            assert report["status"] == "proved" and report["summary"]["obligations"] == 31
            assert report["summary"]["proven"] == 31 and report["trust"]["kernel_replayed_certificates"] == 31
        if expected_reason:
            assert report["status"] == "failed" and report["verification_state"] == "unknown"
            assert report["summary"]["proven"] == report["summary"]["obligations"]
            assert report["summary"]["finding_count"] == 0
    print(name, "admission accounting: " + (expected_reason or "consistent"))
