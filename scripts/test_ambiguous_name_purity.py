"""Duplicate callable names must not shift purity metadata of later declarations."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
run = subprocess.run([str(BINARY), "--json",
                      str(ROOT / "examples/ambiguous_name_purity_probe.elisa")],
                     capture_output=True, text=True, timeout=120)
assert run.returncode == 0, (run.returncode, run.stderr, run.stdout)
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0, report
assert report["status"] == report["verification_state"] == "proved", report
assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
assert report["replay"]["replayed"] == report["summary"]["proven"]
functions = {d["name"]: d for d in report["declaration_details"]
             if d.get("kind") == "function"}
assert functions["scalar_after_collision"]["pure"]
assert not functions["effect_after_collision"]["pure"]
assert functions["pure_after_effect"]["pure"]
assert functions["caller_keeps_started"]["verified"]
negative = subprocess.run([str(BINARY), "--function-json",
    "rejected_effect_preserves_started",
    str(ROOT / "examples/rejected_ambiguous_name_purity.elisa")],
    capture_output=True, text=True, timeout=120)
assert negative.returncode == 1, (negative.returncode, negative.stderr, negative.stdout)
rejected = json.loads(negative.stdout)
assert rejected["summary"]["semantic_errors"] == 0
assert rejected["replay"]["gaps"] == 0 and not rejected["trust"]["trusted_assumptions"]
assert any(f["kind"] == "ensure-unproven" and f["name"] == "rejected_effect_preserves_started"
           for f in rejected["findings"])
print("duplicate names preserve pure/effectful declaration alignment and field facts")
