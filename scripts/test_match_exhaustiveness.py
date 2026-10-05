"""Closed enum matches add a replay-checked constructor disjunction only when complete."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=120)
    return result.returncode, json.loads(result.stdout)


code, data = run("match_exhaustiveness.elisa")
assert code == 0 and data["status"] == "proved", data["findings"]
assert data["summary"]["semantic_errors"] == 0, data["semantic_diagnostics"]
assert data["summary"]["proven"] == data["summary"]["obligations"], data["summary"]
assert data["replay"]["certificates"] == data["replay"]["replayed"] > 0, data["replay"]
assert data["replay"]["gaps"] == 0, data["replay"]
assert any(fact["kind"] == "match-exhaustiveness" for fact in data["trust"]["boundary_facts"])

for name, function in (
    ("rejected_match_omitted_case.elisa", "omitted_case_is_not_exhaustive"),
    ("rejected_match_duplicate_case.elisa", "duplicate_case_is_not_exhaustive"),
    ("rejected_match_wrong_constructor.elisa", "wrong_constructor_is_not_exhaustive"),
):
    code, data = run(name)
    assert code == 1 and data["status"] == "failed", (name, code, data["status"])
    assert any(f["kind"] == "ensure-unproven" and f["name"] == function
               for f in data["findings"]), (name, data["findings"])
    assert not any(fact["kind"] == "match-exhaustiveness"
                   for fact in data["trust"]["boundary_facts"]), name
    assert data["replay"]["gaps"] == 0, (name, data["replay"])

print("match exhaustiveness: complete distinct constructor coverage proves and replays; omitted, duplicate, and foreign cases refuse")
