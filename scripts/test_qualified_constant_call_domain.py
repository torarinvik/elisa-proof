"""Root functions retain module identity when witnessing pure-call arguments."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

BIN = qualified_test_binary.proof_test_binary(ROOT)
for fixture, expected in (("qualified_constant_call_domain", 0),
                          ("rejected_qualified_constant_call_domain", 1)):
    run = subprocess.run([BIN, "--json", str(ROOT / "examples" / (fixture + ".elisa"))],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == expected, (fixture, run.returncode, run.stdout, run.stderr)
    report = json.loads(run.stdout)
    assert report["summary"]["semantic_errors"] == 0, report
    assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
    assert report["replay"]["replayed"] == report["summary"]["proven"]
    if expected == 0:
        assert report["status"] == "proved" and report["findings"] == []
    else:
        failed = {f["name"] for f in report["findings"] if f["kind"] == "ensure-unproven"}
        assert {"rejected_qualified_constant_zero", "rejected_qualified_namespace_equal"} <= failed
print("qualified constant call domains replay; false output and namespace equality reject")
