"""Loop-preservation summary preparation cannot prove an unvisited byte."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def run(fixture):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=90)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    return result.returncode, report


code, positive = run("counted_predicate_prefix.elisa")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["proven"] == positive["summary"]["obligations"] > 0
code, negative = run("rejected_counted_predicate_prefix.elisa")
assert code == 1 and negative["status"] == "failed", negative["findings"]
name = "rejected_unvisited_predicate_byte"
assert any(f["name"] == name and f["kind"] == "ensure-unproven"
           for f in negative["findings"])
assert not any(d.get("name") == name and d.get("verified")
               for d in negative["declaration_details"])
print("Counted predicate prefix replays; unvisited-byte claim rejects")
