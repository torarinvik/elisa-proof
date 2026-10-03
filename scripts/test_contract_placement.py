"""A contract is checked where its kind is read and fails closed anywhere else."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name, expected_status, compiler_placement_lines=()):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / f"{name}.elisa")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected_status, (name, run.returncode, run.stderr, run.stdout)
    data = json.loads(run.stdout)
    # Newer compilers (2678ff10+) also reject a misplaced requires/ensure themselves.
    semantic = [d for d in data.get("semantic_diagnostics", []) if d["severity"] == 1]
    assert all(d["kind_code"] == 172 and d["line"] in compiler_placement_lines for d in semantic), semantic
    assert data["summary"]["semantic_errors"] == len(semantic), data
    assert data["replay"]["gaps"] == 0, data
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data
    return data


accepted = report("contract_placement", 0)
assert accepted["status"] == "proved", accepted
assert accepted["findings"] == [], accepted["findings"]
functions = [d for d in accepted["declaration_details"] if d.get("kind") == "function"]
assert len(functions) == 6 and all(d["verified"] for d in functions), functions

rejected = report("rejected_contract_placement", 1, (12, 24, 33))
assert rejected["status"] == "failed", rejected
found = sorted((f["line"], f["name"], f["kind"]) for f in rejected["findings"])
assert found == [
    (12, "ensure_in_branch", "contract-placement-unsupported"),
    (16, "invariant_outside_loop", "contract-placement-unsupported"),
    (24, "ensure_in_captured_loop", "contract-placement-unsupported"),
    (33, "ensure_in_plain_loop", "contract-placement-unsupported"),
    (40, "measure_in_for_loop", "contract-placement-unsupported"),
    (50, "invariant_in_loop_branch", "contract-placement-unsupported"),
    (57, "changes_in_match_arm", "contract-placement-unsupported"),
    (67, "writing_call_in_captured_invariant", "invariant-not-preserved"),
    (67, "writing_call_in_captured_invariant", "invariant-unproven"),
    (68, "writing_call_in_captured_invariant", "contract-call-unsupported"),
], found

print("contract placement: contracts are checked where read and rejected elsewhere")
