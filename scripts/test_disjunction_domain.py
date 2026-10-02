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
assert len(opened["findings"]) == 1 and opened["findings"][0]["name"] == "open_pure_call_domain"
print("conditional domains replay; false alternatives reject; pure-call integer witness gap remains open")
