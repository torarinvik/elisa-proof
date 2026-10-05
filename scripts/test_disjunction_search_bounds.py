"""Disjunction search bounds preserve fail-closed producer and replay behavior."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def run(source):
    with tempfile.NamedTemporaryFile("w", suffix=".elisa", encoding="utf-8") as stream:
        stream.write(source)
        stream.flush()
        process = subprocess.run(
            [BINARY, "--json", stream.name], capture_output=True, text=True, timeout=60
        )
    report = json.loads(process.stdout)
    assert report["summary"]["semantic_errors"] == 0, report["summary"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
    return process.returncode, report


def late_premise(extra_parameters, dishonest=False):
    parameters = ["accepted: bool", "denied: bool"]
    parameters.extend(f"unrelated_{index}: bool" for index in range(extra_parameters))
    returned = "denied" if dishonest else "accepted"
    return "\n".join(
        [
            f"def late({', '.join(parameters)}) -> bool:",
            "    requires not denied",
            "    requires accepted or denied",
            "    ensure result",
            f"    return {returned}",
            "",
        ]
    )


# Two used parameters, their Boolean type facts, and the two contract facts make
# 16 search facts. The disjunction is the last contract fact and must still be
# checked at the inclusive boundary.
code, at_limit = run(late_premise(12))
assert code == 0 and at_limit["status"] == "proved", at_limit["findings"]

# One additional unrelated typed parameter puts the late relevant premise past
# the fact bound. The proof must become unknown rather than reuse truncated
# search to certify either the valid claim or a false one.
code, over_limit = run(late_premise(13))
assert code == 1 and over_limit["status"] == "failed", over_limit["summary"]
assert any(
    finding["kind"] == "ensure-unproven" and finding["status"] == "unknown"
    for finding in over_limit["findings"]
), over_limit["findings"]
code, false_over_limit = run(late_premise(13, dishonest=True))
assert code == 1 and false_over_limit["status"] == "failed", false_over_limit["summary"]
assert all(finding["status"] != "proved" for finding in false_over_limit["findings"])

# Put a relevant fact after eight and nine irrelevant disjunctions. The call
# goal also exercises the independent replay path; a bounded scan may decline
# to use the late fact, while another complete rule can still certify it.
for candidate_count in (8, 9):
    lines = [
        "def identity(value: bool) -> bool:",
        "    ensure result == value",
        "    return value",
        "",
        "def candidates(accepted: bool) -> bool:",
    ]
    lines.extend("    requires true or false" for _ in range(candidate_count))
    lines.extend(
        [
            "    requires identity(accepted) or false",
            "    ensure identity(accepted)",
            "    return accepted",
            "",
        ]
    )
    code, report = run("\n".join(lines))
    assert code == 0 and report["status"] == "proved", report["findings"]

print("disjunction search bounds: late premises at the fact limit replay; over-limit premises fail closed; candidate-boundary proofs replay")
