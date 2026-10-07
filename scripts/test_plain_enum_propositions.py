"""Ordinary enum members are typed values; another enum's member is refused."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
prover = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "build/elisa-proof"
for name, accepted in (("plain_enum_member_proposition", True),
        ("rejected_plain_enum_owner_proposition", False),
        ("rejected_plain_enum_overloaded_equality", False),
        ("rejected_plain_enum_alias_equality", False),
        ("rejected_plain_enum_comparison_claim", False)):
    result = subprocess.run([str(prover), "--json", str(root / "test/repro" / (name + ".elisa"))],
        capture_output=True, text=True, check=False)
    report = json.loads(result.stdout)
    if accepted:
        assert result.returncode == 0 and report["status"] == "proved", report["summary"]
        assert report["summary"]["unproven"] == 0 and report["replay"]["gaps"] == 0
    else:
        assert result.returncode != 0 and report["status"] != "proved"
        assert report["summary"]["unproven"] > 0 or report["summary"]["semantic_errors"] > 0
        if name != "rejected_plain_enum_owner_proposition":
            assert report["summary"]["semantic_errors"] == 0
        if name in ("rejected_plain_enum_overloaded_equality", "rejected_plain_enum_alias_equality"):
            assert any(finding["kind"] == "expression-unsupported" for finding in report["findings"])
    print(name + (": accepted with complete replay" if accepted else ": refused"))
