"""Boolean locals preserve their initializer facts until reassigned."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def run(fixture):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"].get("trusted_assumptions", [])
    return result.returncode, report


code, positive = run("bool_local_branch_fact.elisa")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0

code, reassigned = run("rejected_reassigned_bool_local_branch_fact.elisa")
assert code == 1 and reassigned["status"] == "failed", reassigned["findings"]
assert any(f["name"] == "read_after_flag_reassignment" and f["kind"] == "index-upper-unproven"
           for f in reassigned["findings"]), reassigned["findings"]
print("Boolean-local branch fact replays; reassigned flag does not retain stale bound")
