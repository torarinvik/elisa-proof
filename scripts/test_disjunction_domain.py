"""OR elimination may discard only explicitly refuted alternatives."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
for fixture, expected in (("disjunction_domain_probe", 0),
                          ("rejected_disjunction_domain_probe", 1)):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (fixture + ".elisa"))],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == expected, (fixture, run.returncode, run.stdout, run.stderr)
    report = json.loads(run.stdout)
    assert report["summary"]["semantic_errors"] == 0, report
    assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
    assert report["replay"]["replayed"] == report["summary"]["proven"]
    if expected == 0:
        assert report["status"] == "proved"
    else:
        failed = {f["name"] for f in report["findings"] if f["kind"] == "ensure-unproven"}
        assert {"rejected_missing_bound", "rejected_missing_alternative"} <= failed
        assert any(f["name"] == "rejected_float_totality" for f in report["findings"])
        float_decl = next(d for d in report["declaration_details"]
                          if d.get("name") == "rejected_float_totality" and d.get("kind") == "function")
        assert not float_decl["verified"]
open_run = subprocess.run([str(BINARY), "--function-json", "open_pure_call_domain",
    str(ROOT / "examples/open_disjunction_call_domain_probe.elisa")],
    capture_output=True, text=True, timeout=120)
assert open_run.returncode == 1, (open_run.returncode, open_run.stdout, open_run.stderr)
opened = json.loads(open_run.stdout)
assert opened["summary"]["semantic_errors"] == 0 and opened["replay"]["gaps"] == 0
assert opened["status"] == "failed" and opened["verification_state"] == "unknown"
assert opened["replay"]["replayed"] == opened["summary"]["proven"]
assert any(f["kind"] == "ensure-unproven" and f["status"] == "unknown"
           for f in opened["findings"]), opened["findings"]

direct_run = subprocess.run([str(BINARY), "--function-json", "direct_pure_call_domain",
    str(ROOT / "examples/open_disjunction_call_domain_probe.elisa")],
    capture_output=True, text=True, timeout=120)
assert direct_run.returncode == 0, (direct_run.returncode, direct_run.stdout, direct_run.stderr)
direct = json.loads(direct_run.stdout)
assert direct["summary"]["semantic_errors"] == 0 and direct["replay"]["gaps"] == 0
assert direct["findings"] == [] and direct["status"] == "proved"
assert direct["replay"]["replayed"] == direct["summary"]["proven"]

repeated_run = subprocess.run([str(BINARY), "--function-json", "repeated_pure_call_domain",
    str(ROOT / "examples/open_disjunction_call_domain_probe.elisa")],
    capture_output=True, text=True, timeout=120)
assert repeated_run.returncode == 1, (repeated_run.returncode, repeated_run.stdout, repeated_run.stderr)
repeated = json.loads(repeated_run.stdout)
assert repeated["summary"]["semantic_errors"] == 0 and repeated["replay"]["gaps"] == 0
assert repeated["status"] == "failed" and repeated["verification_state"] == "unknown"
assert repeated["replay"]["replayed"] == repeated["replay"]["certificates"]
assert any(f["kind"] == "ensure-unproven" and f["status"] == "unknown"
           for f in repeated["findings"]), repeated["findings"]
float_run = subprocess.run([str(BINARY), "--json",
    str(ROOT / "examples/rejected_float_call_integer_domain.elisa")],
    capture_output=True, text=True, timeout=120)
assert float_run.returncode == 1, (float_run.returncode, float_run.stdout, float_run.stderr)
float_report = json.loads(float_run.stdout)
assert float_report["summary"]["semantic_errors"] == 0 and float_report["replay"]["gaps"] == 0
assert not float_report["trust"]["trusted_assumptions"]
assert any(f["name"] == "rejected_float_call_totality" for f in float_report["findings"])
print("conditional domains and pure-call integer bounds replay; false alternatives reject")
