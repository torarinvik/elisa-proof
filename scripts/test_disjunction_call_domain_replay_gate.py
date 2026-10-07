"""Keep call-domain disjunctions source-authenticated and fail closed on local aliases."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
REPLAY_BINARY = os.environ.get("ELISA_PROOF_REPLAY_BIN", str(ROOT / "build/elisa-proof-replay"))


def run_function(name, source):
    with tempfile.NamedTemporaryFile("w", suffix=".elisa", encoding="utf-8") as stream:
        stream.write(source)
        stream.flush()
        process = subprocess.run(
            [BINARY, "--function-json", name, stream.name],
            capture_output=True,
            text=True,
            timeout=180,
        )
    return process.returncode, json.loads(process.stdout)


def run_source(source):
    with tempfile.NamedTemporaryFile("w", suffix=".elisa", encoding="utf-8") as stream:
        stream.write(source)
        stream.flush()
        process = subprocess.run(
            [BINARY, "--json", stream.name], capture_output=True, text=True, timeout=180
        )
    return process.returncode, json.loads(process.stdout)


def export_package(source):
    with tempfile.NamedTemporaryFile("w", suffix=".elisa", encoding="utf-8") as stream:
        stream.write(source)
        stream.flush()
        process = subprocess.run(
            [BINARY, "--package", stream.name], capture_output=True, text=True, timeout=180
        )
    assert process.returncode == 0, process.stderr or process.stdout
    return json.loads(process.stdout)


def replay_package(package):
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as stream:
        json.dump(package, stream)
        stream.flush()
        return subprocess.run(
            [REPLAY_BINARY, stream.name], capture_output=True, text=True, timeout=180
        )


# The historical local-alias gap now closes through independently checked source bindings.
# Preserve complete replay and explicit refusal controls for wrong claims and changed locals.
local_alias = """\
def choice(status: u8) -> u8:
    ensure status > 9 or result == 1 or result >= 3 and result <= 11
    return 1 if status == 0
    return status + 2 if status <= 9
    return 0

def status(value: bool) -> u8:
    ensure result <= 9
    return 9 if value
    return 0

def local_alias(value: bool) -> u8:
    ensure result == 1 or result >= 3 and result <= 11
    local: u8 = status(value)
    return choice(local)
"""
code, bound = run_function("local_alias", local_alias)
assert code == 0 and bound["status"] == "proved", bound["status"]
assert bound["summary"]["semantic_errors"] == 0
assert bound["replay"]["gaps"] == 0
assert bound["replay"]["certificates"] == bound["replay"]["replayed"]
assert not bound["trust"]["trusted_assumptions"]

# Acceptance cannot survive an unrelated result, a wider callee domain, or a
# reassignment between capturing the call result and consuming the local.
controls = (
    local_alias.replace("ensure result == 1 or result >= 3 and result <= 11\n    local:", "ensure result == 2\n    local:"),
    local_alias.replace("ensure result <= 9", "ensure result <= 12").replace("return 9 if value", "return 12 if value"),
    local_alias.replace("local: u8 = status(value)", "local: mutable u8 = status(value)\n    local <- 12"),
)
for control in controls:
    code, refused = run_function("local_alias", control)
    assert code == 1 and refused["status"] == "failed", refused["status"]
    assert refused["replay"]["gaps"] == 0
    assert refused["replay"]["certificates"] == refused["replay"]["replayed"]
    assert not refused["trust"]["trusted_assumptions"]

# Many captures retain their high-fact stress shape and authenticate each source local.
repeated = subprocess.run(
    [BINARY, "--function-json", "repeated_pure_call_domain",
     str(ROOT / "examples/open_disjunction_call_domain_probe.elisa")],
    capture_output=True, text=True, timeout=180,
)
repeated_report = json.loads(repeated.stdout)
assert repeated.returncode == 0 and repeated_report["status"] == "proved"
assert repeated_report["measurements"]["live_facts_peak"] >= 64
assert repeated_report["replay"]["gaps"] == 0
assert repeated_report["replay"]["certificates"] == repeated_report["replay"]["replayed"]
assert not repeated_report["trust"]["trusted_assumptions"]

# Direct composition continues to prove through the checked call-summary disjunction.
positive = """\
def choice(status: u8) -> u8:
    ensure status > 9 or result == 1 or result >= 3 and result <= 11
    return 1 if status == 0
    return status + 2 if status <= 9
    return 0

def direct_positive(status: u8) -> u8:
    requires status <= 9
    ensure result == 1 or result >= 3 and result <= 11
    return choice(status)
"""
code, proved = run_function("direct_positive", positive)
assert code == 0 and proved["status"] == "proved", proved["status"]
assert proved["summary"]["semantic_errors"] == 0 and proved["replay"]["gaps"] == 0
assert proved["replay"]["certificates"] == proved["replay"]["replayed"]
assert not proved["trust"]["trusted_assumptions"]

# An unrelated, false result claim is not rescued by a matching branch inside a call summary.
false_claim = """\
def choose(status: u8) -> u8:
    ensure status > 9 or result == 1 or result >= 3 and result <= 11
    return 3

def false_claim(status: u8) -> u8:
    requires status <= 9
    ensure result == 1
    return choose(status)
"""
code, rejected = run_function("false_claim", false_claim)
assert code == 1 and rejected["status"] == "failed", rejected["status"]
assert rejected["verification_state"] == "unknown"
assert rejected["replay"]["gaps"] == 0
assert all(not (goal["name"] == "false_claim" and goal["rule"] == "goal" and goal["proven"])
           for goal in rejected["goals"]), rejected["goals"]

# Late relevant evidence remains reachable after irrelevant candidates at the search cap.
budget = "\n".join([
    "def identity(value: bool) -> bool:",
    "    ensure result == value",
    "    return value",
    "",
    "def budget_positive(accepted: bool) -> bool:",
    *("    requires true or false" for _ in range(8)),
    "    requires identity(accepted) or false",
    "    ensure identity(accepted)",
    "    return accepted",
    "",
])
code, budget_report = run_source(budget)
assert code == 0 and budget_report["status"] == "proved", budget_report["status"]
assert budget_report["replay"]["gaps"] == 0
assert budget_report["replay"]["certificates"] == budget_report["replay"]["replayed"]

# Portable replay checks the alias package kernel; source correspondence stays an adapter.
alias_package = export_package(local_alias)
alias_replay = replay_package(alias_package)
assert alias_replay.returncode == 0, alias_replay.stderr or alias_replay.stdout
assert json.loads(alias_replay.stdout)["status"] == "replayed"

# Portable replay rejects malformed roots after accepting the positive source package.
package = export_package(positive)
portable = replay_package(package)
assert portable.returncode == 0, portable.stderr or portable.stdout
assert json.loads(portable.stdout)["status"] == "replayed"
mutated = json.loads(json.dumps(package))
theorem = next(item for item in mutated["theorems"]
               if item["name"] == "direct_positive" and item["rule"] == "goal")
theorem["conclusion"] = len(mutated["kernel"]["nodes"]) + 1
malformed = replay_package(mutated)
assert malformed.returncode == 1
malformed_report = json.loads(malformed.stdout)
assert malformed_report["status"] == "rejected"
assert malformed_report["reason"] == "root-out-of-range", malformed_report

print("call-domain disjunction gate: authenticated aliases, reassignment/domain/false-claim refusal, candidate budget, malformed replay")
