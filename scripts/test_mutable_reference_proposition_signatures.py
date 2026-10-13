"""Mutable-reference formals must not be flattened into shared-reference calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


CASES = {
    "direct mutable reference": (
        "direct_mutable_reference_contract",
        False,
        """
def direct_mutable_reference_predicate(value: mutable bool&) -> bool:
    return true

def direct_mutable_reference_contract(value: mutable bool&) -> bool:
    ensure direct_mutable_reference_predicate(value) or true
    return true
""",
    ),
    "aliased mutable reference": (
        "aliased_mutable_reference_contract",
        False,
        """
type MutableBooleanReference = mutable bool&

def aliased_mutable_reference_predicate(value: MutableBooleanReference) -> bool:
    return true

def aliased_mutable_reference_contract(value: MutableBooleanReference) -> bool:
    ensure aliased_mutable_reference_predicate(value) or true
    return true
""",
    ),
    "shared reference control": (
        "shared_reference_contract",
        True,
        """
def shared_reference_predicate(value: bool&) -> bool:
    return true

def shared_reference_contract(value: bool&) -> bool:
    ensure shared_reference_predicate(value) or true
    return true
""",
    ),
    "mutable by-value control": (
        "mutable_value_contract",
        True,
        """
def mutable_value_predicate(value: mutable bool) -> bool:
    return true

def mutable_value_contract(value: mutable bool) -> bool:
    ensure mutable_value_predicate(value) or true
    return true
""",
    ),
}


with tempfile.TemporaryDirectory() as folder:
    for label, (owner, accepted, source) in CASES.items():
        path = Path(folder) / (owner + ".elisa")
        path.write_text(source)
        result = subprocess.run(
            [BINARY, "--json", str(path)], capture_output=True, text=True, timeout=60
        )
        report = json.loads(result.stdout)
        assert report["summary"]["semantic_errors"] == 0, (label, report)
        assert report["replay"]["gaps"] == 0, (label, report["replay"])
        assert report["replay"]["certificates"] == report["replay"]["replayed"], (
            label, report["replay"]
        )
        assert not report["trust"]["trusted_assumptions"], (label, report["trust"])

        type_findings = [
            finding for finding in report["findings"]
            if finding["name"] == owner and finding["kind"] == "contract-proposition-type"
        ]
        if accepted:
            assert result.returncode == 0 and report["status"] == "proved", (label, report)
            assert not type_findings, (label, type_findings)
            assert report["summary"]["proven"] == report["summary"]["obligations"], report
        else:
            # The contracts are tautologies so an ensure-unproven result would mean the call
            # was typed as an ordinary value call instead of being rejected as unsupported.
            assert result.returncode == 1 and report["status"] == "failed", (label, report)
            assert type_findings, (label, report["findings"])

        print("mutable-reference proposition typing:", label, report["status"])
