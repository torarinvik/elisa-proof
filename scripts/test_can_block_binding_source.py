"""Compile capability-block mutable binding and source-authentic scope controls."""
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
source = (ROOT / 'examples/can_block_frame.elisa').read_text()
scalar_module = ast.parse((ROOT / "scripts/test_scalar_copy_bound_source.py").read_text())
scalar_harness = next(ast.literal_eval(node.value.right) for node in scalar_module.body
                      if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "harness" for t in node.targets)
                      and isinstance(node.value, ast.BinOp))
constructor = scalar_harness.split("        def source_gate", 1)[0]
harness = prefix + constructor + r'''
        def source_gate(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            report.replay_owner_line <- 27
            report.trace_owner_line <- 100
            proof_replay_local_binding_mutable_local_source(report, trace, false)

        def scoped_binding_refusal(report: mutable ProofReport&) -> i64:
            for trace in report.traces.records |report|:
                continue if trace.kind != "local-binding" or trace.name != "learns_inside"
                match trace.expression:
                    Ast::Expr.Binary(left, TokenKind.EqEq, right, _):
                        continue if proof_ident_name(left) != "m"
                        match right:
                            Ast::Expr.IntLit(value, _):
                                if value == 10:
                                    return 1 if source_gate(report, trace) else 0
                            _:
                                pass
                    _:
                        pass
            -1

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
    trace_count: usize = report.traces.records.count
    for index in 0..<trace_count |report|:
        candidate: ProofFactTrace = report.traces.records[index]
        continue if candidate.kind != "local-binding" or candidate.line != 32 or candidate.name != "learns_inside"
        match candidate.expression:
            Ast::Expr.Binary(left, TokenKind.EqEq, right, position):
                continue if proof_ident_name(left) != "m"
                return 1 if not source_gate(&report, candidate)
                return 2 if source_gate(&report, forged_trace(candidate, candidate.expression, 31, candidate.kind, 0))
                return 3 if source_gate(&report, forged_trace(candidate, Ast::Expr.Binary(Ast::Expr.Ident("evil", position), TokenKind.EqEq, right, position), 32, candidate.kind, 0))
                return 4 if source_gate(&report, forged_trace(candidate, Ast::Expr.Binary(left, TokenKind.EqEq, Ast::Expr.Ident("b", position), position), 32, candidate.kind, 0))
                __CONTROLS__
                return 0
            _:
                pass
    return 99
'''
controls = {
    "wrong_literal": source.replace("m <- 10", "m <- 9"),
    "later_write": source.replace("    return m", "    m <- 12\n    return m"),
    "block_suffix_write": source.replace("        m <- 10", "        m <- 10\n        m <- 12"),
    "conditional_site": source.replace("        m <- 10", "        if n < 2:\n            m <- 10"),
    "loop_site": source.replace("        m <- 10", "        while n < 2:\n            m <- 10"),
    "conditional_block": source.replace("    can Memory.Allocate:\n        a.push(n)", "    if n < 2:\n        can Memory.Allocate:\n            a.push(n)").replace("        m <- 10", "            m <- 10"),
    "local_shadow": source.replace("        m <- 10", "        m: mutable u32 = 10"),
    "reference_local": source.replace("m: mutable u32 = 0", "m: mutable u32& = n"),
}

lines = []
for number, (name, changed) in enumerate(controls.items(), 10):
    lines += ["other_bytes: mutable darray[u8] = []", "other_report: mutable ProofReport = proof_empty_report()"] if number == 10 else []
    lines += [f"parse_source({json.dumps(changed)}, &other_bytes, &other_report)", f"return {number} if source_gate(&other_report, candidate)"]
for number, name in enumerate(["conditional_site", "loop_site", "conditional_block"], 30):
    lines += [f"parse_source({json.dumps(controls[name])}, &other_bytes, &other_report)", f"return {number} if scoped_binding_refusal(&other_report) != 0"]
harness = harness.replace("__SOURCE__", json.dumps(source)).replace("__CONTROLS__", "\n                ".join(lines))
with tempfile.TemporaryDirectory(prefix="can-block-binding-source-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("capability block binding: direct outer assignment accepted; eleven forged trace/source controls plus three source-authentic scope controls refused")
