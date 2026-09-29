"""Call summaries over struct-construct arguments replay; false controls stay open."""
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


accepted = report("replay_construct_arguments", 0)
assert accepted["status"] == "proved", accepted["status"]
functions = {d["name"]: d for d in accepted["declaration_details"] if d.get("kind") == "function"}
for name in ("from_parameters", "from_literals", "from_bool_field"):
    assert functions[name]["verified"], (name, functions[name])
assert accepted["findings"] == [], accepted["findings"]
rejected = report("rejected_replay_construct_arguments", 1)
found = {(f["name"], f["kind"]) for f in rejected["findings"]}
expected = {(name, "ensure-unproven") for name in (
    "untrue_tighter_cap", "untrue_swapped_fields", "untrue_other_construct")}
assert expected <= found, sorted(expected - found)
print("replay construct arguments: summaries over struct arguments replay; false controls stay open")
