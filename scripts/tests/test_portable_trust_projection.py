"""Unrecognized caller-supplied trust claims must never be projected as replayed proofs."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portable_replay_support import export, refused, with_theorem


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
