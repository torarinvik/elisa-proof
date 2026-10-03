"""Typed sort/bit identity binds real target goals, not stale-fingerprint refusals."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
SOURCE = ROOT / "test/typed_goal_identity_probe.elisa"
if not __debug__:
    raise SystemExit("run without Python -O")


def invoke(*arguments):
    run = subprocess.run([BIN, *map(str, arguments)], capture_output=True, text=True, timeout=60)
    return run.returncode, json.loads(run.stdout)


code, report = invoke("--json", SOURCE)
assert code == 1 and report["summary"]["semantic_errors"] == 0
assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
names = ("typed_u8_identity_positive", "typed_u8_identity_negative",
         "typed_u16_identity_negative", "typed_u64_high_bit_negative")
fingerprints = {}
with tempfile.TemporaryDirectory(prefix="elisa-typed-goal-identity-") as directory:
    script = Path(directory) / "proof.json"
    for name in names:
        goals = [g for g in report["goals"] if g["name"] == name and g["rule"] == "goal"]
        assert len(goals) == 1
        goal = goals[0]
        code, focused = invoke("--goal", goal["goal_id"], SOURCE)
        assert code == 0 and focused["goal_fingerprint"] is not None, name
        fingerprint = focused["goal_fingerprint"]["value"]
        fingerprints[name] = fingerprint
        target = {"goal_id": goal["goal_id"], "goal_fingerprint": fingerprint}
        script.write_text(json.dumps({"format": "elisa-proof-tactics-v1", "target": target,
                                      "actions": [{"action": "simp" if name.endswith("positive") else "decide"}]}))
        code, result = invoke("--tactics", script, SOURCE)
        assert result["source_goal_binding"]["fingerprint_match"] is True, name
        assert result["source_goal_binding"]["goal_fingerprint"]["value"] == fingerprint
        # The current JSON AST mirror erases typed-literal sorts. Exact arena matching
        # must refuse that lossy import, including a true proposition, until the
        # typed tactic transport is implemented. Identity alone never admits a proof.
        assert code == 1 and not result["tactic"]["valid"] and not result["tactic"]["solved"]
        assert result["tactic"]["reason"] == "invalid source-bound proof script", name
        target["goal_fingerprint"] = (fingerprint + 1) % 2**32
        script.write_text(json.dumps({"format": "elisa-proof-tactics-v1", "target": target,
                                      "actions": [{"action": "decide"}]}))
        code, changed = invoke("--tactics", script, SOURCE)
        assert code == 1 and not changed["tactic"]["valid"]
        assert changed["source_goal_binding"]["fingerprint_match"] is False
assert fingerprints["typed_u8_identity_negative"] != fingerprints["typed_u16_identity_negative"]
print("typed identities bind widths/high bits; lossy tactic imports and changed fingerprints fail closed")
