"""Parser-annotated quantifiers reach bounded instantiation, not block rejection."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O: assertions must remain enabled")

def run(fixture):
    p = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                       capture_output=True, text=True, timeout=60)
    r = json.loads(p.stdout)
    assert r["summary"]["semantic_errors"] == 0
    assert r["replay"]["gaps"] == 0
    assert r["replay"]["certificates"] == r["replay"]["replayed"]
    assert not r["trust"]["trusted_assumptions"]
    return p.returncode, r

for fixture in ("quantifier.elisa", "collection_quantifier.elisa",
                "quantifier_structural_terms.elisa", "quantifier_hypothesis.elisa",
                "disjunctive_syllogism_quantified_probe.elisa"):
    code, report = run(fixture)
    assert code == 0 and report["status"] == "proved", (fixture, report["findings"])
    assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
    assert not report["findings"]

negative_targets = {
    "rejected_quantifier.elisa": ("bad_bounded_forall", "too_large_bounded_forall"),
    "rejected_collection_quantifier.elisa": ("bad_collection_forall", "bad_collection_exists",
                                           "empty_collection_exists", "dynamic_collection_is_opaque"),
    "rejected_quantifier_capture.elisa": ("dictionary_key_name_must_not_be_captured",),
    "rejected_duplicate_quantifier.elisa": ("duplicate_dictionary_binder",),
    "quantifier_overflow_rejected.elisa": ("quantified_unsigned_wrap", "quantified_signed_wrap"),
}
for fixture, targets in negative_targets.items():
    code, report = run(fixture)
    assert code == 1 and report["status"] == "failed"
    for target in targets:
        assert any(f["name"] == target for f in report["findings"]), (fixture, report["findings"])
        assert not any(d.get("kind") == "function" and d.get("name") == target and d.get("verified")
                       for d in report["declaration_details"])
    if fixture == "rejected_quantifier.elisa":
        assert any(f["name"] == "too_large_bounded_forall" and f["status"] == "timeout"
                   for f in report["findings"])
print("bounded quantifier dispatch replays; false, empty, dynamic, capture, duplicate and over-budget controls reject")
