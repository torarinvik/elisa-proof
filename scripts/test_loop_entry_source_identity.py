"""An edited source invariant cannot authorize an old loop-entry certificate."""
import ast
import os
from pathlib import Path
from source_binding_harness_support import run_source_binding_replay_harness

ROOT = Path(__file__).resolve().parents[1]
module = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
harness = next(ast.literal_eval(node.value) for node in module.body
               if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "REPLAY_HARNESS"
                       for target in node.targets))
harness = harness.split("    false_bytes: mutable darray[u8] = []")[0] + "    return 0\n"
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Loop-entry identity: edited invariant rejects; restored source replays")
