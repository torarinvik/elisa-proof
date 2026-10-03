"""Failed early-return order guards feed the quotient rule; false controls stay open."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name, code):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (name + ".elisa"))],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == code, (name, run.returncode, run.stderr)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data["summary"]
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data["replay"]
    return data


accepted = report("negated_guard_orders", 0)
functions = {d["name"]: d for d in accepted["declaration_details"] if d.get("kind") == "function"}
for name in ("progress", "proper_fraction", "below_after_guard", "descending_guard"):
    assert functions[name]["verified"], (name, functions[name])
assert accepted["findings"] == [], accepted["findings"]
rejected = report("rejected_negated_guard_orders", 1)
found = {(f["name"], f["kind"]) for f in rejected["findings"]}
expected = {(name, "ensure-unproven") for name in (
    "untrue_tight_progress", "untrue_reversed_guard", "untrue_inclusive_guard")}
assert expected <= found, sorted(expected - found)
print("negated guard orders: failed guards bound quotients; false controls stay open")
