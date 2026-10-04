"""Reserved layout queries are type applications; real bounds remain checked."""

import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, report = run("layout_query_not_index.elisa")
assert code == 0 and report["status"] == "proved", report["findings"]
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
assert report["replay"]["gaps"] == 0
assert report["trust"]["trusted_assumptions"] == []
code, report = run("rejected_fixed_array_constant_index.elisa")
assert code == 1 and report["status"] == "failed", report
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert any(f["kind"] == "index-upper-unproven" and f["status"] == "unknown"
           for f in report["findings"]), report["findings"]
print("layout type application accepted; out-of-range runtime indexing rejected")
