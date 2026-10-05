"""The correlated-disjunction consumer must resolve its product pair together."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
consumer = ast.parse((ROOT / "scripts/test_correlated_disjunction.py").read_text(encoding="utf-8"))

imports_pair = any(
    isinstance(node, ast.ImportFrom) and node.module == "portable_replay_support"
    and {(alias.name, alias.asname) for alias in node.names}
    >= {("BINARY", "PRODUCER"), ("REPLAY", None)}
    for node in ast.walk(consumer)
)
assert imports_pair, "correlated-disjunction consumer must use the shared paired product resolver"
assert not any(
    isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    and node.value.id == "os" and node.attr == "environ"
    for node in ast.walk(consumer)
), "correlated-disjunction consumer must not independently select product overrides"
assert not any(
    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    and isinstance(node.func.value, ast.Name) and node.func.value.id == "Path"
    and node.args and isinstance(node.args[0], ast.Constant)
    and "build/elisa-proof" in str(node.args[0].value)
    for node in ast.walk(consumer)
), "correlated-disjunction consumer must not hardcode product paths"

print("correlated-disjunction product selection: shared proof/replay pair required")
