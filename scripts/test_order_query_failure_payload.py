"""Unknown order-query payloads cannot contribute arithmetic evidence."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("order_query_failure_payload.elisa", True),
                          ("rejected_order_query_failure_payload.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), r["findings"]
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["summary"]["semantic_errors"] == 0
        assert r["status"] == "proved" and not r["findings"]
    else:
        for name in ("rejected_negated_order_strict_increment", "rejected_boolean_as_order"):
            assert any(f["name"] == name and f["kind"] == "ensure-unproven"
                       for f in r["findings"]), (name, r["findings"])
            assert not any(d.get("name") == name and d.get("verified")
                           for d in r["declaration_details"])
print("negated order increment replays; strict-bound and Boolean-as-order claims reject")
