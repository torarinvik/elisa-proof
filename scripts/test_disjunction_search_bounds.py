"""Relevant disjunction search candidates bypass irrelevant facts safely."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
REPLAY_BINARY = os.environ.get("ELISA_PROOF_REPLAY_BIN", str(ROOT / "build/elisa-proof-replay"))


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


def export_package(source):
    with tempfile.TemporaryDirectory() as directory:
        source_path = Path(directory) / "probe.elisa"
        source_path.write_text(source, encoding="utf-8")
        process = subprocess.run(
            [BINARY, "--package", str(source_path)], capture_output=True, text=True, timeout=120
        )
        assert process.returncode == 0, process.stderr or process.stdout
        return json.loads(process.stdout)


def replay_package(package):
    with tempfile.TemporaryDirectory() as directory:
        package_path = Path(directory) / "probe.json"
        package_path.write_text(json.dumps(package), encoding="utf-8")
        process = subprocess.run(
            [REPLAY_BINARY, str(package_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return process.returncode, json.loads(process.stdout)


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

# Keep a passing, single-line control with the same call-summary/disjunction shape as the
# multiline regression. Its certificate must survive standalone replay, while an out-of-range
# conclusion index must be rejected by the portable kernel.
single_line_contract = """\
def identity(value: bool) -> bool:
    ensure result == value
    return value

def single_line_contract(accepted: bool) -> bool:
    requires identity(accepted) or false
    ensure identity(accepted)
    return accepted
"""
single_package = export_package(single_line_contract)
code, single_portable = replay_package(single_package)
assert code == 0 and single_portable["status"] == "replayed", single_portable
single_goal_theorems = [
    theorem for theorem in single_package["theorems"]
    if theorem["name"] == "single_line_contract" and theorem["rule"] == "goal"
]
assert len(single_goal_theorems) == 1, single_goal_theorems
malformed_package = json.loads(json.dumps(single_package))
malformed_goal = next(
    theorem for theorem in malformed_package["theorems"]
    if theorem["name"] == "single_line_contract" and theorem["rule"] == "goal"
)
malformed_goal["conclusion"] = len(malformed_package["kernel"]["nodes"]) + 1
code, malformed = replay_package(malformed_package)
assert code == 1 and malformed["status"] == "rejected", malformed
assert malformed["reason"] == "root-out-of-range", malformed

# The same premises do not justify their negated result. Preserve this false-claim control and
# check that package export omits the open goal rather than turning search recognition into a
# proof.
false_multiline_contract = """\
def identity(value: bool) -> bool:
    ensure result == value
    return value

def false_multiline_contract(accepted: bool) -> bool:
    requires (
        identity(accepted) or false
    )
    ensure (
        not identity(accepted)
    )
    return accepted
"""
code, false_claim = run(false_multiline_contract)
assert code == 1 and false_claim["status"] == "failed", false_claim["findings"]
assert false_claim["summary"]["proven"] < false_claim["summary"]["obligations"], false_claim["summary"]
false_goals = [
    goal for goal in false_claim["goals"]
    if goal["name"] == "false_multiline_contract" and goal["rule"] == "goal"
]
assert len(false_goals) == 1 and not false_goals[0]["proven"], false_goals
false_package = export_package(false_multiline_contract)
assert not any(
    theorem["name"] == "false_multiline_contract" and theorem["rule"] == "goal"
    for theorem in false_package["theorems"]
), false_package["theorems"]

# These premises each have a goal-matching alternative, but their other side
# remains open, so eight/nine of them genuinely fail the entailment check.
def relevant_failures(count, late_success=False):
    parameters = ["accepted: bool"] + [f"other_{index}: bool" for index in range(count)]
    lines = [
        f"def relevant_failures({', '.join(parameters)}) -> bool:",
    ]
    lines.extend(
        f"    requires accepted or other_{index}"
        for index in range(count)
    )
    if late_success:
        lines.extend([f"    requires not other_{count - 1}", f"    requires accepted or other_{count - 1}"])
    lines.extend(["    ensure accepted", "    return accepted", ""])
    return "\n".join(lines)


code, eight_failures = run(relevant_failures(8))
assert code == 1 and eight_failures["status"] == "failed", eight_failures["findings"]
assert any(
    finding["kind"] == "ensure-unproven" and finding["status"] in {"unknown", "timeout"}
    for finding in eight_failures["findings"]
), eight_failures["findings"]
code, nine_failures = run(relevant_failures(9))
assert code == 1 and nine_failures["status"] == "failed", nine_failures["findings"]
assert any(
    finding["kind"] == "ensure-unproven" and finding["status"] in {"unknown", "timeout"}
    for finding in nine_failures["findings"]
), nine_failures["findings"]

# Repeated-call locals now have independently authenticated source bindings.
# Keep their full replay and live-fact workload alongside the refusal/search-cap controls.
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
assert domain_report["verification_state"] == "proved", domain_report["verification_state"]
assert domain_report["replay"]["gaps"] == 0, domain_report["replay"]
assert domain_report["replay"]["certificates"] == domain_report["replay"]["replayed"]
assert not domain_report["trust"]["trusted_assumptions"]
assert domain_report["findings"] == [], domain_report["findings"]

# A later refuted alternative can still be established by the independent
# disjunctive-syllogism rule after the bounded entailment scan stops.
code, late_success = run(relevant_failures(9, late_success=True))
assert code == 0 and late_success["status"] == "proved", late_success["findings"]
assert late_success["replay"]["gaps"] == 0
assert late_success["replay"]["certificates"] == late_success["replay"]["replayed"]
assert late_success["measurements"]["producer_disjunction_refutation_checks"] > 0

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

print("disjunction search: late premises replay, and authenticated local aliases replay while false/search-cap claims remain refused")

# Preserve this unrelated multiline positive assertion unchanged and run it after the high-fact
# controls, so its known source/replay mismatch cannot mask the later bounded-search regressions.
multiline_contract = """\
def identity(value: bool) -> bool:
    ensure result == value
    return value

def multiline_contract(accepted: bool) -> bool:
    requires (
        identity(accepted) or false
    )
    ensure (
        identity(accepted)
    )
    return accepted
"""
code, multiline = run(multiline_contract)
assert code == 0 and multiline["status"] == "proved", multiline["findings"]
