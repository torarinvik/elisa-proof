"""Scalar scan changes must not admit source-overloaded primitive semantics."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")

for fixture in (
    "rejected_overloaded_primitive_rewrite",
    "rejected_overloaded_primitive_global_rewrite",
    "rejected_overloaded_literal_equality",
    "rejected_overloaded_literal_fact",
    "rejected_overloaded_literal_rewrite",
    "rejected_overloaded_runtime_assert",
):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (fixture + ".elisa"))],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 1, (fixture, run.returncode, run.stderr, run.stdout)
    report = json.loads(run.stdout)
    assert report["status"] == "failed", (fixture, report)
    assert report["summary"]["semantic_errors"] == 0, (fixture, report)
    assert report["replay"]["gaps"] == 0, (fixture, report)
    assert report["replay"]["certificates"] == report["replay"]["replayed"], (fixture, report)
    assert not report["trust"]["trusted_assumptions"], (fixture, report)
    assert any(f["kind"] == "ensure-unproven" and f["status"] in ("unknown", "unsupported")
               for f in report["findings"]), (fixture, report)
    assert not any(g["rule"] == "goal" and g["proven"] for g in report["goals"]), (fixture, report)
    print(fixture + ": rejected without replay gaps")
