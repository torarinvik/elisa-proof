"""Stored unsigned call results use this invocation's checked summary."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/local_call_result_binding_probe.elisa"
if not __debug__:
    raise SystemExit("run without Python -O: assertions must remain enabled")

def run(target):
    p = subprocess.run([BIN, "--function-json", target, str(SOURCE)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert r["summary"]["semantic_errors"] == 0
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"] > 0
    assert not r["trust"]["trusted_assumptions"]
    leaf = [d for d in r["declaration_details"] if d.get("name") == "checked_zero"]
    assert len(leaf) == 1 and leaf[0]["verified"] and not leaf[0]["pure"]
    return p.returncode, r

code, positive = run("stored_checked_zero")
assert code == 0 and positive["status"] == "proved", positive["findings"]
assert not positive["findings"]
for target, kind in (("stored_checked_zero_wrong", "ensure-unproven"),
                     ("missing_checked_zero_precondition", "call-requires-unproven"),
                     ("shadowed_checked_zero_wrong", "ensure-unproven")):
    code, negative = run(target)
    assert code == 1 and negative["status"] == "failed"
    assert any(f["name"] == target and f["kind"] == kind for f in negative["findings"]), negative["findings"]
print("stored checked result replays; wrong result, missing precondition and shadow controls reject")

p = subprocess.run([BIN, "--function-json", "wrong_narrowed_result",
                    str(ROOT / "examples/local_call_result_width_rejected.elisa")],
                   capture_output=True, text=True, timeout=60)
r = json.loads(p.stdout)
assert p.returncode == 1 and r["status"] == "failed"
assert r["replay"]["gaps"] == 0
assert not r["trust"]["trusted_assumptions"]
assert not any(d.get("name") == "wrong_narrowed_result" and d.get("verified")
               for d in r["declaration_details"])
assert r["summary"]["semantic_errors"] > 0 or any(
    f["name"] == "wrong_narrowed_result" and f["kind"] == "ensure-unproven"
    for f in r["findings"])
print("mismatched-width result cannot manufacture an inconsistent destination bound")
