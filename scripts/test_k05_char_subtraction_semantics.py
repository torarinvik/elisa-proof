"""Record the pinned compiler's character subtraction behavior and proof refusal."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPILER = os.environ.get("ELISA_COMPILER_BIN")
PROOF = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not COMPILER:
    raise SystemExit("set ELISA_COMPILER_BIN to the pinned stage1 compiler")

semantics = ROOT / "examples/k05_char_subtraction_semantics.elisa"
subprocess.run([COMPILER, str(semantics), "-o", "/tmp/k05-char-subtraction.o"], check=True)

result = subprocess.run(
    [PROOF, "--json", str(ROOT / "examples/rejected_k05_char_digit_bound.elisa")],
    capture_output=True, text=True, check=False, timeout=60,
)
report = json.loads(result.stdout)
assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
assert report["replay"]["gaps"] == 0, report["replay"]
goal = next(item for item in report["goals"] if item["rule"] == "goal")
assert not goal["proven"] and goal["refusal_gate"] == "wrap-guard-goal", goal
print("char subtraction compiles in char and i64 return contexts; digit-range proof remains refused")
