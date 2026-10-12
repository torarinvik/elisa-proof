"""An impure proof block cannot certify its enclosing guard or function."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/rejected_impure_proof.elisa"
for route in (("--json",), ("--function-json", "impure_proof")):
    result = subprocess.run([BINARY, *route, str(SOURCE)], capture_output=True,
                            text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == 1 and report["status"] == "failed", (route, report)
    assert report["summary"]["semantic_errors"] == 0, (route, report["semantic_diagnostics"])
    assert report["replay"]["gaps"] == 0, (route, report["replay"])
    assert report["replay"]["certificates"] == report["replay"]["replayed"], (route, report["replay"])
    assert report["trust"]["trusted_assumptions"] == [], (route, report["trust"])
    assert any(finding["kind"] == "proof-impure" and finding["name"] == "impure_proof"
               for finding in report["findings"]), (route, report["findings"])
    assert not any(goal["name"] == "impure_proof" and goal["rule"] == "goal" and goal["proven"]
                   for goal in report["goals"]), (route, report["goals"])
    details = {detail["name"]: detail for detail in report["declaration_details"]}
    assert not details["impure_proof"]["verified"], (route, details["impure_proof"])

print("Impure proof block: guard and declaration remain unverified")
