"""Regression for exact typed usize sentinels in resource-source postconditions."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/unsigned_resource_source_policy.elisa"

for name in ("negative_integer_literal_reflexivity", "usize_max_reflexivity"):
    literal_run = subprocess.run(
        [str(BINARY), "--json", str(ROOT / f"examples/{name}.elisa")],
        capture_output=True, text=True, timeout=60)
    assert literal_run.returncode == 0, (name, literal_run.stderr, literal_run.stdout)
    literal_report = json.loads(literal_run.stdout)
    assert literal_report["status"] == literal_report["verification_state"] == "proved", literal_report
    assert literal_report["summary"]["semantic_errors"] == literal_report["summary"]["semantic_diagnostics"] == 0, literal_report
    assert literal_report["replay"]["certificates"] == literal_report["replay"]["replayed"] > 0, literal_report
    assert literal_report["replay"]["gaps"] == 0 and literal_report["trust"]["trusted_assumptions"] == [], literal_report

run = subprocess.run([str(BINARY), "--json", str(SOURCE)], capture_output=True,
                     text=True, timeout=60)
assert run.returncode == 0, (run.returncode, run.stderr, run.stdout)
report = json.loads(run.stdout)
assert report["status"] == report["verification_state"] == "proved", report
assert report["summary"]["semantic_errors"] == report["summary"]["semantic_diagnostics"] == 0, report
assert report["summary"]["obligations"] > 0
assert report["summary"]["proven"] == report["summary"]["obligations"], report
assert report["replay"]["certificates"] == report["replay"]["replayed"] == report["summary"]["proven"], report
assert report["replay"]["gaps"] == 0 and report["trust"]["trusted_assumptions"] == [], report

policy = next(item for item in report["declaration_details"]
              if item.get("name") == "resource_source_policy")
assert policy["verified"] and policy["ensures"] == 5, policy
single_clause = next(item for item in report["declaration_details"]
                     if item.get("name") == "resource_source_policy_memory_only")
assert single_clause["verified"] and single_clause["ensures"] == 1, single_clause

print("unsigned resource-source policy: all five clauses and usize::MAX fallback replay")
