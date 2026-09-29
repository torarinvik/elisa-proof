"""Call-summary dispatcher budget: a 24-statement body with one call target proves within the
bounded fact headroom; a 40-statement body is refused with a budget finding and never proves."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, data = run("dispatcher_budget.elisa")
assert code == 0 and data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["replay"]["gaps"] == 0 and data["summary"]["semantic_errors"] == 0

code, data = run("rejected_dispatcher_budget.elisa")
assert code == 1 and data["status"] == "failed"
found = [(f["kind"], f["name"]) for f in data["findings"]]
assert found == [("control-flow-analysis-budget", "dispatch_too_long")], found
detail = {d["name"]: d for d in data["declaration_details"]}
assert not detail["dispatch_too_long"]["verified"]
assert data["replay"]["gaps"] == 0

print("dispatcher budget: window admits 24 statements, refuses 40 with a budget finding")
