"""Counterexample assignments must preserve the independently established domain."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def findings(fixture):
    run = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / fixture)],
        capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == 1, (fixture, run.returncode, run.stderr)
    report = json.loads(run.stdout)
    assert report["replay"]["gaps"] == 0, fixture
    assert report["replay"]["certificates"] == report["replay"]["replayed"], fixture
    return {row["name"]: row for row in report["findings"] if row["kind"] == "ensure-unproven"}


boolean = findings("counterexample_boolean_domains.elisa")
for name in ("boolean_parameter_counterexample", "boolean_equality_counterexample"):
    row = boolean[name]
    assert row["status"] == "disproved" and row["counterexample_found"], row
    assert row["counterexample"], row
    assert all(term["right"]["kind"] == "bool" for term in row["counterexample"]), row
for name in ("ambiguous_boolean_equality", "ambiguous_character_equality"):
    row = boolean[name]
    assert row["status"] == "unknown" and not row["counterexample_found"], row
    assert row["counterexample"] == [], row

integer = findings("counterexample_domain.elisa")
exact = integer["exact_scalar_counterexample"]
assert exact["status"] == "disproved" and exact["counterexample_found"], exact
assert exact["counterexample"][0]["right"]["kind"] == "int", exact
assert exact["counterexample"][0]["right"]["value"] == 0, exact
wrapped = integer["narrow_wrap_is_not_a_counterexample"]
assert wrapped["status"] == "unknown" and not wrapped["counterexample_found"], wrapped
assert wrapped["counterexample"] == [], wrapped
print("counterexample domains: typed Boolean/integer models retained; ambiguous and wrapping models refused")
