"""Regression for branch facts read from a mutable reference field.

A cursor bound from `allocator.last` through an if/elif/else ladder must keep
both branch facts, so the callee's `requires` are established at the call. The
prover built from e2fadd8 reports call-requires-unproven for both; until the
region flow is fixed this check fails with the summary below.
"""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
prover = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "build/elisa-proof"
result = subprocess.run(
    [str(prover), "--json", str(root / "test/repro/region_branch_facts.elisa")],
    capture_output=True, text=True, timeout=30,
)
try:
    report = json.loads(result.stdout)
except json.JSONDecodeError:
    raise SystemExit(f"prover produced no report: {(result.stdout or result.stderr)[:1000]}")
summary = report.get("summary", {})
proven = summary.get("proven", 0)
obligations = summary.get("obligations", 0)
failed = summary.get("failed", len(report.get("diagnostics", [])))
assert report.get("status") == "proved" and failed == 0 and proven == obligations, (
    f"region_branch_facts regression: status={report.get('status')} "
    f"proven={proven}/{obligations} failed={failed}"
)
print("region_branch_facts PASS")
