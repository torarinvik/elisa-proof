"""Sums, constant multiples, variable-divisor quotients and relational clamps order; false controls stay open."""
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


accepted = report("monotone_orders", 0)
functions = {d["name"]: d for d in accepted["declaration_details"] if d.get("kind") == "function"}
for name in ("clamped_sum", "crossed_sum", "inclusive_sum", "descending_sum", "strict_share",
             "inclusive_share", "proper_fraction", "unscaled_share", "below_sum", "below_multiple"):
    assert functions[name]["verified"], (name, functions[name])
assert accepted["findings"] == [], accepted["findings"]
rejected = report("rejected_monotone_orders", 1)
found = {(f["name"], f["kind"]) for f in rejected["findings"]}
expected = {(name, "ensure-unproven") for name in (
    "untrue_strict_sum", "untrue_clamped_sum", "untrue_loose_operand", "untrue_full_share",
    "untrue_small_limit", "untrue_relational_clamp", "untrue_below_sum", "untrue_zero_multiple")}
assert expected <= found, sorted(expected - found)
print("monotone orders: sums, multiples, quotients and relational clamps replay; false controls stay open")
