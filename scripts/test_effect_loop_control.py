"""Loop control adds no call edge, but cannot hide effects or imply exhaustion."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")

def inspect(name):
    run = subprocess.run([BIN, "--json", str(ROOT / "examples" / (name + ".elisa"))],
                         capture_output=True, text=True, timeout=60)
    report = json.loads(run.stdout)
    assert report["summary"]["semantic_errors"] == 0, report.get("semantic_diagnostics")
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    return run.returncode, report

code, positive = inspect("effect_loop_control")
assert code == 0 and positive["status"] == "proved", positive["findings"]
for name in ("effect_break_keeps_value", "effect_continue_keeps_value"):
    assert any(g["name"] == name and g["rule"] == "effect-containment" and g["replay_status"] == "replayed" for g in positive["goals"]), name
code, negative = inspect("rejected_effect_loop_control")
assert code == 1 and negative["status"] == "failed"
assert any(f["name"] == "rejected_effect_break_implies_exhaustion" and f["kind"] == "ensure-unproven" for f in negative["findings"])
assert any(f["name"] == "rejected_effect_call_before_break" and f["kind"] == "effect-row-exceeded" for f in negative["findings"])
assert any(f["name"] == "rejected_effect_call_in_captured_loop" and f["kind"] == "effect-row-exceeded" for f in negative["findings"])
print("Break/continue effect coverage replays; false exhaustion and hidden foreign effects reject")
