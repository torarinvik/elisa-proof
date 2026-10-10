"""Source locals capture one invocation, never repeatable non-pure call text."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
for name, accepted in (
    ("arithmetic_call_result_alias", True),
    ("call_result_literal_alias", True),
    ("signed_call_result_chain", True),
    ("signed_call_result_chain_rejected", False),
    ("rejected_arithmetic_call_result_alias", False),
    ("call_result_wrong_alias_rejected", False),
    ("call_result_distinct_invocations_rejected", False),
):
    result = subprocess.run([BINARY, "--json", str(ROOT / "test/repro" / (name + ".elisa"))], capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == (0 if accepted else 1), (name, report["summary"])
    assert report["admission_invariant_failure"] == "", (name, report["admission_invariant_failure"])
    if accepted:
        assert report["status"] == "proved"
        assert report["summary"]["proven"] == report["summary"]["obligations"]
        assert report["trust"]["kernel_replayed_certificates"] == report["summary"]["obligations"]
    else:
        assert report["summary"]["unproven"] > 0 and report["summary"]["finding_count"] > 0
    print("source call result:", name, report["status"], report["trust"]["kernel_replayed_certificates"])
