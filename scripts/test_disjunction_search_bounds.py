"""Relevant disjunction search candidates bypass irrelevant facts safely."""
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
            [BINARY, "--json", stream.name], capture_output=True, text=True, timeout=120
        )
    report = json.loads(process.stdout)
    assert report["summary"]["semantic_errors"] == 0, report["summary"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
    return process.returncode, report


# The target premise follows eight unrelated disjunctions. They must not use
# the candidate budget in either the producer or independent replay kernel.
source = "\n".join(
    [
        "def identity(value: bool) -> bool:",
        "    ensure result == value",
        "    return value",
        "",
        "def late_relevant(accepted: bool) -> bool:",
        *("    requires true or false" for _ in range(8)),
        "    requires identity(accepted) or false",
        "    ensure identity(accepted)",
        "    return accepted",
        "",
    ]
)
code, late = run(source)
assert code == 0 and late["status"] == "proved", late["findings"]

# The high-fact pure-call domain case regressed under a raw fact-count guard.
# Keep it in this focused boundary suite so producer and replay retain coverage.
domain = subprocess.run(
    [
        BINARY,
        "--function-json",
        "repeated_pure_call_domain",
        str(ROOT / "examples/open_disjunction_call_domain_probe.elisa"),
    ],
    capture_output=True,
    text=True,
    timeout=180,
)
domain_report = json.loads(domain.stdout)
assert domain.returncode == 0 and domain_report["status"] == "proved", domain_report["findings"]
assert domain_report["summary"]["semantic_errors"] == 0, domain_report["summary"]
assert domain_report["replay"]["gaps"] == 0, domain_report["replay"]
assert domain_report["replay"]["certificates"] == domain_report["replay"]["replayed"]
assert not domain_report["trust"]["trusted_assumptions"]

print("disjunction search: late relevant facts survive irrelevant candidates and high-fact domains replay")
