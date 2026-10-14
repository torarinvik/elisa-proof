"""Replay the quotient-based half-open window bound and reject its boundary case."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

BINARY = Path(qualified_test_binary.proof_test_binary(ROOT))
run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/unsigned_quotient_window.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
)
assert run.returncode == 1, (run.returncode, run.stderr)
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0, report["replay"]
functions = {
    declaration["name"]: declaration
    for declaration in report["declaration_details"]
    if declaration.get("kind") == "function"
}
assert functions["every_in_range_chunk_window_ends_within_total"]["verified"], functions
assert functions["a_count_bound_by_quotient_contains_every_window"]["verified"], functions
assert not functions["index_at_quotient_may_exceed_total"]["verified"], functions
assert not functions["an_unlinked_count_does_not_bound_a_window"]["verified"], functions
assert not functions["a_count_from_a_different_size_does_not_bound_a_window"]["verified"], functions
findings = {
    (finding["name"], finding["kind"])
    for finding in report["findings"]
}
assert ("index_at_quotient_may_exceed_total", "ensure-unproven") in findings, findings
assert ("an_unlinked_count_does_not_bound_a_window", "ensure-unproven") in findings, findings
assert ("a_count_from_a_different_size_does_not_bound_a_window", "ensure-unproven") in findings, findings
print("unsigned quotient window bound replays; the one-past-quotient case stays open")
