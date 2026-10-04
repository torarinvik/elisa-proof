"""Literal disequality simplification grants no new predicate truth."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("quantified_prefix_exit.elisa", True),
                          ("rejected_literal_false_quantified_disjunction.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), r["findings"]
    assert r["summary"]["semantic_errors"] == 0 and r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["status"] == "proved" and not r["findings"]
    else:
        for name in ("rejected_false_success_rows", "rejected_different_literals_are_false"):
            assert any(f["name"] == name and f["kind"] == "ensure-unproven" for f in r["findings"])
print("literal-false quantified success contracts replay; missing row evidence and false literal claims reject")
