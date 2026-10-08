"""An exact loop assignment introduces one source-bound fresh witness identity."""
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
# Reuse the genuine loop-entry/preservation setup and its exact-span forgery.
# The broader harness continues into independent invariant and cast controls.
marker = "    # The old RHS witness is invalid once the actual source assignment changes."
assert harness.count(marker) == 1
harness = harness.split(marker)[0] + "    return 132 if not proof_replay_fact_trace_entry(&baseline, rebind_index)\n    return 0\n"
provenance = run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Loop witness identity: genuine source bindings replay; renamed witness rejects; restored report replays")
print(provenance)
