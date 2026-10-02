"""False-left search normalization preserves proofs and rejects missing truth."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("run without Python -O")
root = Path(__file__).resolve().parents[1]
binary = os.environ.get("ELISA_PROOF_BIN", str(root / "build/elisa-proof"))
reports = []
for _ in range(2):
    run = subprocess.run(
        [binary, "--json", str(root / "examples/false_left_search.elisa")],
        capture_output=True, text=True, timeout=30,
    )
    assert run.returncode == 1, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "failed"
    assert report["summary"]["semantic_errors"] == 0
    assert report["summary"]["obligations"] == 14
    assert report["summary"]["proven"] == 12
    assert report["replay"] == {"certificates": 12, "replayed": 12, "gaps": 0}
    assert not report["trust"]["trusted_assumptions"]
    rejected = {"rejected_false_left_unknown_predicate", "rejected_false_left_denied_predicate"}
    assert {(f["name"], f["kind"]) for f in report["findings"]} == {
        (name, "ensure-unproven") for name in rejected
    }
    positive = {
        "false_left_known_predicate", "false_left_nested_disjunction",
        "false_literal_left_known_predicate", "true_left_does_not_require_right",
        "unknown_left_uses_right",
    }
    declarations = {d["name"]: d for d in report["declaration_details"]}
    assert all(declarations[name]["verified"] for name in positive)
    assert all(not declarations[name]["verified"] for name in rejected)
    reports.append(report)
assert reports[0] == reports[1], "proof output must repeat identically"
print("False-left proofs replay 12/12 identically; unknown and denied truth reject")
