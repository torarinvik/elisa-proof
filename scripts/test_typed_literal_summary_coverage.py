"""Typed-literal admission must remain independently verified within analysis caps."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")

root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
run = subprocess.run(
    [binary, "--function-json", "proof_kernel_replay_arena_shape_valid",
     str(root / "examples/kernel_replay_standalone.elisa")],
    capture_output=True, text=True, timeout=120,
)
assert run.returncode == 0, (run.returncode, run.stderr, run.stdout[:2000])
report = json.loads(run.stdout)
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
assert report["findings"] == [], report["findings"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"] == report["summary"]["proven"]
assert not report["trust"]["trusted_assumptions"]
required = {"typed_literal_fields_valid", "typed_literal_sort", "typed_literal_maximum",
            "typed_literal_value", "proof_kernel_replay_arena_scalar_shape",
            "proof_kernel_replay_arena_scalar_shape_for_kind",
            "proof_kernel_replay_arena_shape_valid"}
verified = {row["name"] for row in report["declaration_details"]
            if row["kind"] == "function" and row["verified"]}
assert required <= verified, sorted(required - verified)
print("typed-literal helpers and arena admission: complete summaries, replayed within unchanged caps")
