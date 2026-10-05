"""Foreach element lower bounds follow the exact unsigned iterable and binder."""
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
result = subprocess.run(
    [BINARY, "--json", str(ROOT / "examples/foreach_element_lower_bound.elisa")],
    capture_output=True,
    text=True,
    timeout=30,
)
assert result.returncode == 1, result.stderr
report = json.loads(result.stdout)
assert report["status"] == "failed"  # Expected open upper-bound and negative-control goals.
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
assert not report["trust"]["trusted_assumptions"]

lower_bounds = {
    goal["name"]: goal
    for goal in report["goals"]
    if goal["rule"] == "index-lower"
}
assert set(lower_bounds) == {
    "read_at_nonnegative_foreach_index",
    "keep_signed_foreach_index_unproven",
    "keep_other_index_unproven",
}

valid = lower_bounds["read_at_nonnegative_foreach_index"]
assert valid["proven"] and valid["replay_status"] == "replayed", valid
assert any(origin["kind"] == "loop-range" for origin in valid["fact_origins"])
assert any(
    fact.get("kind") == "binary"
    and fact.get("operator") == "<="
    and fact.get("left", {}).get("kind") == "int"
    and fact["left"].get("value") == 0
    and fact.get("right", {}).get("kind") == "tuple"
    and fact["right"].get("elements", [{}])[0].get("name") == "index"
    for fact in valid["facts"]
), valid["facts"]

# A signed iterable cannot borrow the element type of a separate unsigned array.
wrong_array = lower_bounds["keep_signed_foreach_index_unproven"]
assert not wrong_array["proven"] and wrong_array["replay_status"] == "not_certified", wrong_array
assert wrong_array["goal"]["right"]["elements"][0]["name"] == "index"

# Even inside an unsigned foreach, the fact belongs only to that loop's binder, not an outer i64.
wrong_binder = lower_bounds["keep_other_index_unproven"]
assert not wrong_binder["proven"] and wrong_binder["replay_status"] == "not_certified", wrong_binder
assert wrong_binder["goal"]["right"]["kind"] == "ident"
assert wrong_binder["goal"]["right"]["name"] == "index"
assert not any(
    fact.get("kind") == "binary"
    and fact.get("operator") == "<="
    and fact.get("left", {}).get("kind") == "int"
    and fact["left"].get("value") == 0
    and fact.get("right", {}).get("kind") == "tuple"
    and fact["right"].get("elements", [{}])[0].get("name") == "index"
    for fact in wrong_binder["facts"]
), wrong_binder["facts"]

print("Unsigned foreach index lower bounds replay; signed-array and wrong-binder controls stay open")
