"""Focused synchronization gate for constant tactic replay and machine refusals."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))

if not __debug__:
    raise SystemExit("run without Python -O")


def report(fixture, source, expected):
    run = subprocess.run(
        [str(BINARY), "--tactics", str(ROOT / "examples" / fixture),
         str(ROOT / "examples" / source)],
        capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == expected, (fixture, run.returncode, run.stderr)
    return json.loads(run.stdout)


positive = report("tactic_script_safe_small_constant_simp.json", "replay_constant.elisa", 0)
assert positive["status"] == "proved", positive
tactic = positive["tactic"]
assert tactic["valid"] is True and tactic["solved"] is True, positive
assert tactic["kernel_trace_replayed"] is True, positive
assert tactic["certificate_replayed"] is True, positive

for fixture, goal, fingerprint in (
    ("rejected_u64_max_decide", 7, 515359733),
    ("rejected_u8_overflow_decide", 13, 1229197265),
    ("rejected_u8_overflow_simp", 13, 1229197265),
):
    negative = report("tactic_script_" + fixture + ".json",
                      "rejected_u64_max_conflict.elisa", 1)
    assert negative["status"] == "failed", negative
    binding = negative["source_goal_binding"]
    assert binding["goal_id"] == goal, negative
    assert binding["fingerprint_match"] is True, negative
    assert binding["goal_fingerprint"]["value"] == fingerprint, negative
    assert negative["tactic"]["valid"] is False, negative
    assert negative["tactic"]["solved"] is False, negative

print("constant replay: safe simplification replayed; three machine-invalid claims refused")
