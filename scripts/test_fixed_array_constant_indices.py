"""Fixed-array literal indices stay proved in unsigned contexts and reject overflow."""
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


positive = report("fixed_array_constant_indices.elisa", 0)
assert positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
assert all(goal["proven"] and goal["replay_status"] == "replayed"
           for goal in positive["goals"]), positive

negative = report("rejected_fixed_array_constant_index.elisa", 1)
assert negative["status"] == "failed", negative
assert negative["replay"]["gaps"] == 0, negative
assert negative["replay"]["certificates"] == negative["replay"]["replayed"], negative
assert any(finding["kind"] == "index-upper-unproven"
           for finding in negative["findings"]), negative

print("fixed-array literal indices: in-range proof replayed; first out-of-range index refused")
