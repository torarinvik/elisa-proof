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


# Irrelevant disjunctions do not consume the candidate budget before the
# relevant premise, in either the producer or independent replay kernel.
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

# These premises each have a goal-matching alternative, but their other side
# remains open, so eight/nine of them genuinely fail the entailment check.
def relevant_failures(count, late_success=False):
    parameters = ["accepted: bool"] + [f"other_{index}: bool" for index in range(count)]
    lines = [
        "def opaque(value: bool) -> bool:",
        "    return value",
        "",
        f"def relevant_failures({', '.join(parameters)}) -> bool:",
    ]
    lines.extend(
        f"    requires opaque(accepted) or opaque(other_{index})"
        for index in range(count)
    )
    if late_success:
        lines.append("    requires opaque(accepted) or false")
    lines.extend(["    ensure opaque(accepted)", "    return accepted", ""])
    return "\n".join(lines)


code, eight_failures = run(relevant_failures(8))
assert code == 1 and eight_failures["status"] == "failed", eight_failures["findings"]
assert any(
    finding["kind"] == "ensure-unproven" and finding["status"] == "unknown"
    for finding in eight_failures["findings"]
), eight_failures["findings"]
code, nine_failures = run(relevant_failures(9))
assert code == 1 and nine_failures["status"] == "failed", nine_failures["findings"]
assert any(
    finding["kind"] == "ensure-unproven" and finding["status"] == "unknown"
    for finding in nine_failures["findings"]
), nine_failures["findings"]

# A later refuted alternative can still be established by the independent
# disjunctive-syllogism rule after the bounded entailment scan stops.
code, late_success = run(relevant_failures(9, late_success=True))
assert code == 0 and late_success["status"] == "proved", late_success["findings"]

# A premise with no goal-matching branch but with every branch refuted was
# accepted by the old entailment rule. Preserve that contradiction case.
contradiction = """\
def opaque(value: bool) -> bool:
    return value

def contradiction(value: bool, q: bool, r: bool) -> bool:
    requires not q
    requires not r
    requires q or r
    ensure opaque(value)
    return value
"""
code, contradictory = run(contradiction)
assert code == 0 and contradictory["status"] == "proved", contradictory["findings"]

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
