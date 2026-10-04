"""High-arity, bounded selectors get bounded headroom and still replay."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


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
assert functions["parameter_heavy_manifest_route_contract"]["verified"], functions
# The old implication was reversed: it demanded zero for valid kinds. Keep it
# as an adversarial control instead of teaching the verifier to accept it.
with tempfile.TemporaryDirectory(prefix="elisa-proof-selector-contract-") as scratch:
    false_source = Path(scratch) / "reversed_implication.elisa"
    text = SOURCE.read_text()
    correct = "ensures kind <= WbRuntime::RESOURCE_KIND_COMPONENT_INSTANCES or result == 0"
    assert text.count(correct) == 2
    false_source.write_text(text.replace(correct, correct.replace("<=", ">"), 1))
    false_run = subprocess.run([str(BINARY), "--json", str(false_source)],
                               capture_output=True, text=True, timeout=60)
    assert false_run.returncode == 1, (false_run.returncode, false_run.stderr)
    false_report = json.loads(false_run.stdout)
    assert false_report["summary"]["semantic_errors"] == 0, false_report["summary"]
    assert false_report["replay"]["gaps"] == 0, false_report["replay"]
    assert false_report["trust"]["trusted_assumptions"] == [], false_report["trust"]
    assert any(f["kind"] == "ensure-unproven" and f["name"] == "parameter_heavy_manifest_route"
               for f in false_report["findings"]), false_report["findings"]
    assert not next(d for d in false_report["declaration_details"]
                    if d["name"] == "parameter_heavy_manifest_route")["verified"]
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
# Its module constants carry their own fact headroom, so the body may run out of steps first.
# Either way it stays at the ordinary 64 limit and unverified.
assert budget["budget"]["dimension"] in ("facts", "steps"), budget
assert budget["budget"]["limit"] == 64 and budget["budget"]["observed"] > 64, budget
over_limit_functions = {item["name"]: item for item in over_limit["declaration_details"]
                        if item.get("kind") == "function"}
assert not over_limit_functions["parameter_heavy_manifest_route_over_limit"]["verified"], over_limit_functions
print("parameter-heavy return analysis: all obligations and certificates replay")
