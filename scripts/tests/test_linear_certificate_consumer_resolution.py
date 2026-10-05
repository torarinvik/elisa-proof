"""Keep the linear certificate consumer on the shared generation-pinned pair."""
import ast
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "test_linear_certificates.py"
tree = ast.parse(SCRIPT.read_text())

shared_pair_import = any(
    isinstance(node, ast.ImportFrom)
    and node.module == "portable_replay_support"
    and {alias.name for alias in node.names} >= {"BINARY", "REPLAY"}
    for node in ast.walk(tree)
)
assert shared_pair_import, "linear consumer must use the shared resolved BINARY/REPLAY pair"

independent_selection = any(
    isinstance(node, ast.Constant)
    and isinstance(node.value, str)
    and node.value in {"ELISA_PROOF_BIN", "ELISA_PROOF_REPLAY_BIN"}
    for node in ast.walk(tree)
)
assert not independent_selection, "linear consumer must not independently select either executable"

print("linear certificate consumer: shared generation-pinned pair")
