"""Chains of three or more `or` operands, as facts and as goals. Each disjunct of a chained
precondition is a case whatever the nesting, a chained goal needs one provable disjunct, and a
chain unrelated to the goal must not stop the range facts beside it from proving it (the retry
without top-level disjunctive facts). An uncovered case, a goal no disjunct satisfies, a claim
past the range and a five-case off-by-one stay unproven, and a true six-case chain is refused\nat the split budget (four nested splits), as a timeout rather than a disproof."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=600)
    return json.loads(result.stdout)


data = run(ROOT / "examples/or_chain.elisa")
assert data["status"] == "proved" and data["findings"] == [], (data["summary"], data["findings"])
assert data["replay"]["gaps"] == 0 and data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]

data = run(ROOT / "examples/rejected_or_chain.elisa")
assert data["status"] != "proved"
assert data["replay"]["gaps"] == 0
assert all(f["status"] != "proved" for f in data["findings"])
assert sorted((f["name"], f["line"], f["refusal_gate"], f["status"]) for f in data["findings"]
              if f["kind"] == "ensure-unproven") == [
    ("chain_does_not_tighten_range", 21, "unknown", "unknown"), ("five_case_off_by_one", 26, "connective", "disproved"),
    ("nested_uncovered_case", 11, "unknown", "disproved"), ("no_disjunct_holds", 15, "connective", "disproved"),
    ("six_case_budget", 33, "budget", "timeout"), ("uncovered_case", 6, "connective", "disproved")], data["findings"]

print("or chains: chains up to five disjuncts split, chained goals introduce, uncovered cases and the six-case budget refused")
