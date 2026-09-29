"""High-arity, bounded selectors get bounded headroom and still replay."""
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/parameter_heavy_return_analysis.elisa"
OVER_LIMIT_SOURCE = ROOT / "examples/parameter_heavy_return_analysis_over_limit.elisa"
run = subprocess.run([str(BINARY), "--json", str(SOURCE)],
                     capture_output=True, text=True, timeout=60)
assert run.returncode == 0, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["status"] == report["verification_state"] == "proved", report.get("findings")
assert report["summary"]["obligations"] == report["summary"]["proven"] > 0, report["summary"]
assert report["summary"]["failed"] == 0 and report["summary"]["semantic_diagnostics"] == 0, report["summary"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0, report["replay"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["trust"]["trusted_assumptions"] == [], report["trust"]
functions = {item["name"]: item for item in report["declaration_details"]
             if item.get("kind") == "function"}
assert functions["parameter_heavy_manifest_route"]["verified"], functions
over_limit_run = subprocess.run([str(BINARY), "--json", str(OVER_LIMIT_SOURCE)],
                                capture_output=True, text=True, timeout=60)
assert over_limit_run.returncode == 1, (over_limit_run.returncode, over_limit_run.stderr)
over_limit = json.loads(over_limit_run.stdout)
assert over_limit["status"] == "failed" and over_limit["verification_state"] == "unsupported", over_limit
assert over_limit["summary"]["semantic_errors"] == 0, over_limit["summary"]
assert over_limit["replay"]["gaps"] == 0, over_limit["replay"]
assert over_limit["replay"]["certificates"] == over_limit["replay"]["replayed"], over_limit["replay"]
budget = next(f for f in over_limit["findings"]
              if f["kind"] == "control-flow-analysis-budget")
assert budget["budget"] == {"dimension": "facts", "observed": 65, "limit": 64}, budget
print("parameter-heavy return analysis: all obligations and certificates replay")
