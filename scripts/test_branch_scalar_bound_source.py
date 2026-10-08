"""Compile source reconstruction and forgery controls for both branch arms."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")).resolve()
FRONTEND = ROOT / "build/snapshot/Elisa-compiler"
module = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
template = next(ast.literal_eval(node.value) for node in module.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "REPLAY_HARNESS" for t in node.targets))
prefix = template.split("extend ElisaProof:", 1)[0]
prefix = prefix.replace("../../Elisa-compiler/", str(FRONTEND.resolve()) + "/")
prefix = prefix.replace("../src/", str(ROOT / "src") + "/")
source = "def keep_or_replace(flag: bool, slot: usize, best: usize) -> usize:\n    requires best <= 8\n    requires slot < 8\n    ensure result <= 8\n    b: mutable usize = best\n    if flag:\n        b <- slot\n    b\n"
scalar_module = ast.parse((ROOT / "scripts/test_scalar_copy_bound_source.py").read_text())
scalar_harness = next(ast.literal_eval(node.value.right) for node in scalar_module.body
                      if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "harness" for t in node.targets)
                      and isinstance(node.value, ast.BinOp))
constructor = scalar_harness.split("        def source_gate", 1)[0]
harness = prefix + constructor + r'''
        def source_gate(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            report.replay_owner_line <- 1
            report.trace_owner_line <- 8
            proof_replay_branch_scalar_bound_source(report, trace)

def parse_source(text: sview, bytes: mutable darray[u8]&, report: mutable ProofReport&) -> void:
    bytes.clear()
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    proof_check(file, report)

def main() -> i64:
    bytes: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    parse_source(__SOURCE__, &bytes, &report)
    for index in 0..<report.traces.records.count |report, bytes|:
        candidate: ProofFactTrace = report.traces.records[index]
        continue if candidate.kind != "branch-join"
        match candidate.expression:
            Ast::Expr.Binary(left, TokenKind.LtEq, right, position):
                continue if proof_ident_name(left) != "b"
                match right:
                    Ast::Expr.IntLit(value, _):
                        continue if value != 8
                    _:
                        continue
                return 1 if not source_gate(&report, candidate)
                return 2 if not proof_replay_fact_trace_entry(&report, index)
                return 3 if source_gate(&report, forged_trace(candidate, candidate.expression, 7, candidate.kind, 0))
                return 4 if source_gate(&report, forged_trace(candidate, candidate.expression, 6, "proof-step", 0))
                return 5 if source_gate(&report, forged_trace(candidate, candidate.expression, 6, candidate.kind, 1))
                __CONTROLS__
                return 0
            _:
                pass
    return 99
'''
controls = {
    "missing_initial_bound": source.replace("requires best <= 8", "requires best <= 9"),
    "missing_assignment_bound": source.replace("requires slot < 8", "requires slot < 10"),
    "later_write": source.replace("    b\n", "    b <- 9\n    b\n"),
    "wrong_target": source.replace("b: mutable usize", "other: mutable usize").replace("b <- slot", "other <- slot").replace("    b\n", "    other\n"),
    "arithmetic_assignment": source.replace("b <- slot", "b <- slot + 1"),
    "unbounded_else": source.replace("    b\n", "    else:\n        b <- 9\n    b\n"),
    "primitive_alias": source + "\ntype usize = u64\n",
    "wrong_condition_type": source.replace("flag: bool", "flag: usize"),
    "extra_arm_write": source.replace("        b <- slot", "        b <- slot\n        b <- 9"),
}
lines = []
for index, (name, text) in enumerate(controls.items(), 10):
    lines += [f"other_{index}: mutable ProofReport = proof_empty_report()",
              f"parse_source({json.dumps(text)}, &bytes, &other_{index})",
              f"return {index} if source_gate(&other_{index}, candidate)"]
harness = harness.replace("__SOURCE__", json.dumps(source)).replace("__CONTROLS__", "\n                ".join(lines))
with tempfile.TemporaryDirectory(prefix="branch-source-controls-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("branch source: complete authentic trace replays; 12 forged trace/source controls refused")
