"""Loop-range interval bounds admit safe scaled indices and reject the first unsafe range."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(fixture, expected_status):
    run = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / fixture)],
        capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == expected_status, (fixture, run.returncode, run.stderr)
    return json.loads(run.stdout)


positive = report("vector_index_arithmetic_probe.elisa", 0)
assert positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["trust"]["trusted_assumptions"] == [], positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
assert all(goal["proven"] and goal["replay_status"] == "replayed"
           for goal in positive["goals"]), positive

negative = report("rejected_vector_index_arithmetic.elisa", 1)
assert negative["status"] == "failed", negative
assert negative["summary"]["semantic_errors"] == 0, negative
assert negative["trust"]["trusted_assumptions"] == [], negative
assert negative["replay"]["gaps"] == 0, negative
assert negative["replay"]["certificates"] == negative["replay"]["replayed"], negative
assert any(finding["kind"] == "index-upper-unproven"
           for finding in negative["findings"]), negative

underflow = report("rejected_vector_index_underflow.elisa", 1)
assert underflow["status"] == "failed", underflow
assert underflow["summary"]["semantic_errors"] == 0, underflow
assert underflow["trust"]["trusted_assumptions"] == [], underflow
assert underflow["replay"]["gaps"] == 0, underflow
assert underflow["replay"]["certificates"] == underflow["replay"]["replayed"], underflow
assert any(finding["kind"] == "index-lower-unproven"
           for finding in underflow["findings"]), underflow

print("scaled vector indices: safe loop bounds replay; out-of-range and underflow controls refused")
