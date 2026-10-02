"""Automatic finite forall elimination must replay and reject unsound instances."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("universal_premise_auto.elisa", True),
                          ("rejected_universal_premise_auto.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), r["findings"]
    assert r["summary"]["semantic_errors"] == 0
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["status"] == "proved" and not r["findings"]
    else:
        for name in ("rejected_existential_instance", "rejected_empty_instance",
                     "rejected_future_instance", "rejected_unsigned_range_wrap"):
            assert any(f["name"] == name and f["kind"] == "ensure-unproven" for f in r["findings"]), r["findings"]
            assert not any(d.get("name") == name and d.get("verified") for d in r["declaration_details"])
probe = subprocess.run([BIN, "--json", str(ROOT / "examples/open_history_length_prefix.elisa")],
                       capture_output=True, text=True, timeout=60)
r = json.loads(probe.stdout)
assert probe.returncode == 1 and r["summary"]["proven"] == 16 and r["summary"]["obligations"] == 17
assert r["replay"]["certificates"] == r["replay"]["replayed"] == 16 and r["replay"]["gaps"] == 0
assert not r["trust"]["trusted_assumptions"]
assert len(r["findings"]) == 1 and r["findings"][0]["kind"] == "ensure-unproven"
print("automatic finite universal instances and loop preservation replay; existential, empty, future and wrapping controls reject; exit remains open")
