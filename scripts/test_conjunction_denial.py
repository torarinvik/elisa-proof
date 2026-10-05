"""Exact conjunction contradictions replay; disjunctions do not imply operands."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")
root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
for example, code in (("conjunction_denial_probe", 0), ("rejected_disjunction_denial", 1)):
    process = subprocess.run([binary, "--json", str(root / "examples" / (example + ".elisa"))],
                             capture_output=True, text=True, timeout=120)
    assert process.returncode == code, (example, process.returncode, process.stderr)
    report = json.loads(process.stdout)
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0
    assert report["replay"]["certificates"] == report["replay"]["replayed"] == report["summary"]["proven"]
    assert report["trust"]["trusted_assumptions"] == []
    if code == 0:
        assert report["status"] == "proved" and report["findings"] == []
        assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
    else:
        assert report["status"] == "failed"
        assert {row["name"] for row in report["findings"] if row["kind"] == "ensure-unproven"} == {
            "disjunction_is_not_a_conjunction", "unrelated_negation_is_not_a_denial"}
print("conjunction denial: nested and mirrored contradictions replay; disjunction and wrong-atom controls refuse")
