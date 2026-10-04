"""Unused module constants do not consume branch-state budgets or erase shadows."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O: regression assertions must remain enabled")


def run(fixture, expected):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=120)
    report = json.loads(result.stdout)
    assert result.returncode == expected, (fixture, report["findings"])
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert report["replay"]["gaps"] == 0 and not report["trust"]["trusted_assumptions"]
    return report


for fixture in ("global_constant_relevance.elisa", "global_constant_module.elisa",
                "module_u32_scoped_constant_branch.elisa", "module_negative_i64_constant_contract.elisa",
                "module_qualified_global_constant_contract.elisa", "qualified_constant_pins.elisa",
                "extend_scope_local_u8_constant.elisa", "extend_scoped_constant_branch_bound.elisa",
                "fixed_array_constant_indices.elisa"):
    report = run(fixture, 0)
    assert report["status"] == "proved" and not report["findings"]
    if fixture == "global_constant_relevance.elisa":
        assert sum(f["kind"].startswith("global-constant") for f in report["trust"]["boundary_facts"]) == 1
for fixture in ("rejected_global_constant_collision.elisa",
                "rejected_global_constant_usize_collision.elisa",
                "rejected_global_constant_function_collision.elisa",
                "rejected_module_u32_scoped_constant_branch.elisa",
                "rejected_qualified_global_constant_boundary.elisa"):
    report = run(fixture, 1)
    assert any(f["kind"] == "ensure-unproven" for f in report["findings"]), (fixture, report["findings"])
print("relevant module constants replay within unchanged budgets; namespace shadows still reject false claims")
