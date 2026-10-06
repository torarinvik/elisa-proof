"""Return-analysis fuel scales with source shape but always fails closed at its cap."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def function(name: str, statements: int) -> str:
    body = "\n".join("    pass" for _ in range(statements))
    return f"def {name}() -> void:\n{body}\n"


# The two equal-size functions must receive identical structural budgets regardless of name.
# The second name was formerly given a special 128-step allowance.
source = "\n".join((
    function("ordinary_short", 20),
    function("proof_kernel_replay_expr_equal", 20),
    function("bounded_over_limit", 200),
))

with tempfile.TemporaryDirectory(prefix="elisa-return-analysis-budget-") as scratch:
    path = Path(scratch) / "budget.elisa"
    path.write_text(source)
    run = subprocess.run([str(BINARY), "--json", str(path)],
                         capture_output=True, text=True, timeout=60)

assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["status"] == "failed" and report["verification_state"] == "unsupported", report
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["trust"]["trusted_assumptions"] == [], report["trust"]

functions = {item["name"]: item for item in report["declaration_details"]
             if item.get("kind") == "function"}
assert functions["ordinary_short"]["verified"], functions
assert functions["proof_kernel_replay_expr_equal"]["verified"], functions
assert not functions["bounded_over_limit"]["verified"], functions

budget = next(f for f in report["findings"]
              if f["kind"] == "control-flow-analysis-budget"
              and f["name"] == "bounded_over_limit")
assert budget["budget"] == {"dimension": "steps", "observed": 193, "limit": 192}, budget
assert not any(f["kind"] == "control-flow-analysis-budget"
               and f["name"] in ("ordinary_short", "proof_kernel_replay_expr_equal")
               for f in report["findings"]), report["findings"]

print("return-analysis step budget: structural scaling and hard exhaustion verified")
