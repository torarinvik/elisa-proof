"""Unrecognized caller-supplied trust claims must never be projected as replayed proofs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portable_replay_support import BINARY, REPLAY, export, refused, with_theorem


package = export("branch_negation")
assert package["source"]["authenticated"] is False
theorem = package["theorems"][0]

# Existing checks cover upgrades of the known trust fields (e.g. hypotheses="kernel") and
# source.authenticated=true. These adjacent claims try to smuggle an independent trust summary
# or axiom declaration through fields that this package version does not define.
claims = (
    ("top-level-kernel-trust", lambda claim: claim.update(kernel_trust="trusted")),
    ("top-level-assumptions", lambda claim: claim.update(
        trusted_assumptions=["caller asserts every theorem"])),
    ("nested-kernel-label", lambda claim: claim["trust"].update(kernel="trusted")),
    ("nested-assumption-injection", lambda claim: claim["trust"].update(
        assumptions=["unreviewed axiom: False"])),
)

for name, inject in claims:
    forged = with_theorem(package, theorem)
    inject(forged)
    result = refused(forged, "trust-projection-" + name, "malformed",
                     "package-schema" if name.startswith("top-level") else "trust-schema")
    assert result["theorems"] == [], (name, result)
    assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, (name, result)

print("portable trust projection: unknown kernel/assumption claims are refused without theorem publication")

# The separate source-correspondence ingress must independently reject an attempted upgrade of
# adapter-supplied hypotheses. Standalone kernel replay accepts valid packages with those
# hypotheses explicitly classified as adapter input; it must not turn a forged trust label into
# checked source correspondence.
package = export("branch_negation")
source = Path(__file__).resolve().parents[2] / "examples" / "branch_negation.elisa"
with tempfile.TemporaryDirectory(prefix="elisa-trust-correspondence-") as directory:
    package_path = Path(directory) / "package.json"
    package_path.write_text(json.dumps(package, separators=(",", ":")), encoding="utf-8")
    portable = subprocess.run([str(REPLAY), str(package_path)], capture_output=True,
                              text=True, timeout=120)
    portable_result = json.loads(portable.stdout)
    assert portable.returncode == 0 and portable_result["status"] == "replayed", portable_result
    assert portable_result["summary"]["replayed"] == len(package["theorems"]), portable_result
    valid = subprocess.run([str(BINARY), "--correspondence", str(package_path), str(source)],
                           capture_output=True, text=True, timeout=120)
    valid_result = json.loads(valid.stdout)
    assert valid.returncode == 0 and valid_result["package"]["status"] == "replayed", valid_result
    assert valid_result["summary"]["coverage"] == "complete", valid_result

    forged = with_theorem(package, package["theorems"][0])
    forged["trust"]["hypotheses"] = "kernel"
    package_path.write_text(json.dumps(forged, separators=(",", ":")), encoding="utf-8")
    rejected = subprocess.run([str(BINARY), "--correspondence", str(package_path), str(source)],
                              capture_output=True, text=True, timeout=120)
    rejected_result = json.loads(rejected.stdout)
    assert rejected.returncode == 1, rejected_result
    assert rejected_result["package"] == {
        "status": "malformed", "reason": "trust-schema", "theorems": 0, "replayed": 0,
    }, rejected_result
    assert rejected_result["functions"] == [], rejected_result
    assert rejected_result["summary"]["checked"] == 0, rejected_result

print("portable trust projection: forged kernel-trust label is rejected by independent correspondence ingress")
