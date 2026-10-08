"""Compile source-boundary checks for indexed-copy consequences and forged traces."""
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
control_module = ast.parse((ROOT / "scripts/test_index_copy_bounds.py").read_text())
source = next(ast.literal_eval(node.value) for node in control_module.body
              if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SOURCE" for t in node.targets))
scalar_module = ast.parse((ROOT / "scripts/test_scalar_copy_bound_source.py").read_text())
scalar_harness = next(ast.literal_eval(node.value.right) for node in scalar_module.body
                      if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "harness" for t in node.targets)
                      and isinstance(node.value, ast.BinOp))
constructor = scalar_harness.split("        def source_gate", 1)[0]
harness = prefix + constructor + r'''
        def source_gate(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            report.replay_owner_line <- 1
            report.trace_owner_line <- 9
            proof_replay_index_copy_bound_source(report, trace)

        def range_shape(expression: Ast::Expr) -> bool:
            proof_replay_index_copy_range(expression).known

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
        if candidate.kind == "precondition":
            match candidate.expression:
                Ast::Expr.Block(statements, body, captures, block_position):
                    if statements.count == 1:
                        match statements[0]:
                            Ast::Stmt.VarDecl(binder, _, initializer, statement_position):
                                return 13 if not range_shape(candidate.expression)
                                opaque: darray[Ast::Stmt] = [Ast::Stmt.VarDecl(binder, Ast::Expr.Ident("Opaque", statement_position), initializer, statement_position)]
                                return 14 if range_shape(Ast::Expr.Block(opaque, body, captures, block_position))
                                captured: darray[sview] = ["p"]
                                return 15 if range_shape(Ast::Expr.Block(statements, body, captured, block_position))
                            _:
                                pass
                _:
                    pass
        continue if candidate.kind != "proof-step" or candidate.line != 7
        match candidate.expression:
            Ast::Expr.Binary(left, TokenKind.LtEq, right, position):
                continue if proof_ident_name(left) != "p" or proof_ident_name(right) != "a"
                return 1 if not source_gate(&report, candidate)
                return 2 if source_gate(&report, forged_trace(candidate, candidate.expression, 8, candidate.kind, 0))
                return 3 if source_gate(&report, forged_trace(candidate, Ast::Expr.Binary(Ast::Expr.Ident("evil", position), TokenKind.LtEq, right, position), 7, candidate.kind, 0))
                return 4 if source_gate(&report, forged_trace(candidate, Ast::Expr.Binary(left, TokenKind.LtEq, Ast::Expr.Ident("evil", position), position), 7, candidate.kind, 0))
                return 5 if source_gate(&report, forged_trace(candidate, Ast::Expr.Binary(left, TokenKind.EqEq, right, position), 7, candidate.kind, 0))
                return 6 if source_gate(&report, forged_trace(candidate, candidate.expression, 7, "local-binding", 0))
                return 7 if source_gate(&report, forged_trace(candidate, candidate.expression, 7, candidate.kind, 1))
                other_bytes: mutable darray[u8] = []
                alias_report: mutable ProofReport = proof_empty_report()
                parse_source(__ALIAS__, &other_bytes, &alias_report)
                return 8 if source_gate(&alias_report, candidate)
                range_report: mutable ProofReport = proof_empty_report()
                parse_source(__WRONG_RANGE__, &other_bytes, &range_report)
                return 9 if source_gate(&range_report, candidate)
                shadow_report: mutable ProofReport = proof_empty_report()
                parse_source(__SHADOW__, &other_bytes, &shadow_report)
                return 10 if source_gate(&shadow_report, candidate)
                prefix_report: mutable ProofReport = proof_empty_report()
                parse_source(__PREFIX__, &other_bytes, &prefix_report)
                return 11 if source_gate(&prefix_report, candidate)
                return 0
            _:
                pass
    return 12
'''
for marker, text in {
    "__SOURCE__": source,
    "__ALIAS__": source + "\ntype i64 = u64\n",
    "__WRONG_RANGE__": source.replace("t in i..<j", "t in (i + 1)..<j"),
    "__SHADOW__": source.replace("forall t", "forall p").replace("xs[t]", "xs[p]"),
    "__PREFIX__": source.replace("    requires n <= xs.count", "    xs[i] <- p - 1"),
}.items():
    harness = harness.replace(marker, json.dumps(text))
with tempfile.TemporaryDirectory(prefix="index-copy-bound-source-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("indexed-copy source: authentic bound/range accepted; twelve forged trace/source/range controls refused")
