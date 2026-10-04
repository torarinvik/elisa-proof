#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${ELISA_PROOF_BIN:-$ROOT/build/elisa-proof}"
python3 - "$ROOT" "$BIN" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1])
binary = Path(sys.argv[2]).resolve(strict=True)
assert __debug__, "run without Python -O"
assert all(p.stat().st_mtime_ns <= binary.stat().st_mtime_ns
           for p in (root / "src").rglob("*.elisa")), "stale prover"

def run(name):
    process = subprocess.run([str(binary), "--json", str(root / "examples" / name)],
                             capture_output=True, text=True, timeout=30)
    report = json.loads(process.stdout)
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0
    assert report["replay"]["certificates"] == report["replay"]["replayed"] == report["summary"]["proven"]
    assert not report["trust"]["trusted_assumptions"]
    return process.returncode, report

code, positive = run("logical_join_islands.elisa")
assert code == 0 and positive["status"] == positive["verification_state"] == "proved"
assert positive["summary"]["proven"] == positive["summary"]["obligations"] == 8
assert not positive["findings"]
assert positive == run("logical_join_islands.elisa")[1]
assert all(row.get("verified") for row in positive["declaration_details"] if row["kind"] == "function")
code, negative = run("rejected_logical_join_islands.elisa")
assert code == 1 and negative["status"] == "failed"
assert {finding["name"] for finding in negative["findings"]} == {"wrong_island_polarity", "wrong_island_connective"}
assert all(finding["kind"] == "ensure-unproven" for finding in negative["findings"])
print("Mixed Boolean islands replay 8 obligations; wrong connective/polarity reject")
PY
