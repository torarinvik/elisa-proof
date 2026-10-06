"""The prover admits compiler-validated affine state transitions, and no others."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
POSITIVE = ROOT / "examples/typestate_resource_transition.elisa"
NEGATIVE = ROOT / "examples/rejected_typestate_transition_missing_edge.elisa"
if not __debug__:
    raise SystemExit("run without Python -O: assertions must remain enabled")


def report(source):
    result = subprocess.run([BIN, "--json", str(source)], capture_output=True,
                            text=True, timeout=120)
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"proof checker did not return JSON: {result.stderr}") from error
    return result.returncode, parsed


code, good = report(POSITIVE)
assert code == 0 and good["status"] == "proved", good.get("findings")
assert good["summary"]["semantic_errors"] == 0
assert good["summary"]["proven"] == good["summary"]["obligations"]
assert good["findings"] == []
assert good["replay"]["certificates"] == good["replay"]["replayed"] > 0
assert good["replay"]["gaps"] == 0
assert good["trust"]["trusted_assumptions"] == []
resource_goals = {
    goal["name"] for goal in good["goals"]
    if goal["rule"] == "resource-safety" and goal["proven"]
}
assert {"publish", "probe", "main"} <= resource_goals

code, bad = report(NEGATIVE)
assert code == 1 and bad["status"] != "proved"
assert bad["summary"]["semantic_errors"] > 0
assert bad["replay"]["gaps"] == 0
close = [function for function in bad["functions"] if function["name"] == "close"]
assert len(close) == 1 and not close[0]["proved"]
assert any(finding["name"] == "close" and finding["kind"] == "expression-unsupported"
           for finding in bad["findings"])
assert bad["trust"]["trusted_assumptions"] == []
print("legal affine typestate transition replays; missing graph edge is semantically refused")
