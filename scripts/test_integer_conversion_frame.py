"""Only witnessed primitive zero-argument conversions are non-mutating frames."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, positive in (("integer_conversion_frame.elisa", True),
                          ("rejected_custom_conversion_frame.elisa", False)):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == (0 if positive else 1), r["findings"]
    assert r["replay"]["gaps"] == 0 and r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    if positive:
        assert r["status"] == "proved" and not r["findings"]
        assert r["summary"]["semantic_errors"] == 0
    else:
        for name in ("rejected_custom_conversion_frame", "rejected_integer_method_with_argument"):
            assert any(f["name"] == name for f in r["findings"]), r["findings"]
            assert not any(d.get("name") == name and d.get("verified") for d in r["declaration_details"])
for fixture, name in (("rejected_effectful_numeric_cast_contract.elisa", "rejected_effectful_status_cast"),
                      ("rejected_overloaded_conversion_frame.elisa", "rejected_overloaded_conversion_nonzero")):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)], capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert p.returncode == 1 and r["replay"]["gaps"] == 0 and r["replay"]["certificates"] == r["replay"]["replayed"]
    assert any(f["name"] == name for f in r["findings"]), r["findings"]
    assert not any(d.get("name") == name and d.get("verified") for d in r["declaration_details"])
print("primitive integer conversions preserve frames; custom, argument-taking, effectful and overloaded controls reject")
