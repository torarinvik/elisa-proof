"""Qualified builtin call-result types keep Stage1's exact integer widths."""
import json
from pathlib import Path
import subprocess

from qualified_test_binary import proof_test_binary


ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)
source = ROOT / "examples" / "qualified_type_bound_builtins.elisa"
run = subprocess.run([BINARY, "--json", str(source)], capture_output=True,
                     text=True, timeout=60)
report = json.loads(run.stdout)
assert run.returncode == 0 and report["status"] == "proved", (run.returncode, report)
assert report["source"]["admissible"] is True, report["source"]
assert report["summary"]["semantic_errors"] == 0, report["summary"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]
functions = {row["name"]: row["proved"] for row in report["functions"]}
for name in (
    "qualified_builtin_missing_i64_wraps",
    "qualified_owner_alias_shadows_builtin_wraps",
    "qualified_module_root_alias_wraps",
):
    assert functions.get(name) is True, (name, functions)

print("qualified builtin type-bound widths match source semantics and replay")
