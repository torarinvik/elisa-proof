"""Quantifier body search must use relevant instances without raising budgets."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, expected in (("quantified_prefix_step_instances.elisa", "proved"),
                          ("rejected_quantified_prefix_step_instances.elisa", "failed")):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == (0 if expected == "proved" else 1), report["findings"]
    assert report["status"] == expected
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    if expected == "proved":
        assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
    else:
        assert any(f["name"] == "rejected_quantified_prefix_skips_row" and f["kind"] == "ensure-unproven"
                   for f in report["findings"]), report["findings"]
print("quantified one-row prefix step independently replays; skipped-row claim rejects")
