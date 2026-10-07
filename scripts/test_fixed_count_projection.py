"""Fixed-array access certificates derive safety from a count equality."""
import json
import os
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def logical(value):
    if isinstance(value, dict):
        return {key: logical(item) for key, item in value.items()
                if key not in {"line", "column", "offset", "end_line", "end_column", "end_offset"}}
    if isinstance(value, list):
        return [logical(item) for item in value]
    return value


for fixture, accepted in (
    ("fixed_array_bounds", True),
    ("fixed_array_fields", True),
    ("fixed_array_constant_indices", True),
    ("fixed_array_slice_bounds", True),
    ("rejected_fixed_array_bounds", False),
    ("rejected_fixed_array_constant_index", False),
    ("rejected_fixed_array_slice_bounds", False),
):
    result = subprocess.run([BINARY, "--json", str(ROOT / "examples" / (fixture + ".elisa"))],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == (0 if accepted else 1), (fixture, report["summary"])
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0, (fixture, report["replay"])
    assert not report["trust"]["trusted_assumptions"]
    upper = [certificate for certificate in report["certificates"]
             if certificate["rule"] in {"index-upper", "slice-upper"}]
    for certificate in upper:
        typed = [fact for fact, origin in zip(certificate["facts"], certificate["fact_origins"])
                 if origin["kind"] == "type-bound"]
        assert all(logical(fact) != logical(certificate["goal"]) for fact in typed), fixture
        assert any(fact.get("kind") == "binary" and fact.get("operator") == "=="
                   and fact.get("left", {}).get("kind") == "field"
                   and fact["left"].get("field") == "count"
                   and fact.get("right", {}).get("kind") == "int" for fact in typed), fixture
    if accepted:
        assert upper and all(certificate["replayed"] for certificate in upper)
    else:
        assert any(finding["kind"] in {"index-upper-unproven", "slice-upper-unproven"}
                   for finding in report["findings"]), fixture
    print("fixed count:", fixture, "proved" if accepted else "refused")
