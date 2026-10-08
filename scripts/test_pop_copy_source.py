"""Compile source-boundary checks for copied pop literal replay and unchanged snapshot source controls."""
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
source = (ROOT / 'examples/collection_pop_value.elisa').read_text()
scalar_module = ast.parse((ROOT / "scripts/test_scalar_copy_bound_source.py").read_text())
scalar_harness = next(ast.literal_eval(node.value.right) for node in scalar_module.body
                      if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "harness" for t in node.targets)
                      and isinstance(node.value, ast.BinOp))
constructor = scalar_harness.split("        def source_gate", 1)[0]
harness = prefix + constructor + r'''
        def source_gate(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            report.replay_owner_line <- 2
            report.trace_owner_line <- 6
            proof_replay_pop_copy_source(report, trace)

        def audit(report: mutable ProofReport&) -> i64:
            proof_replay_certificates(report)
            return 1 if report.certificates.count != 8
            for certificate in report.certificates |report|:
                return 20 + certificate.line.i64() if not certificate.replayed
            trace_count: usize = report.traces.records.count
            for trace_index in 0..<trace_count |report|:
                trace: ProofFactTrace = report.traces.records[trace_index]
                continue if trace.kind != "proof-step" or trace.name != "take_last" or trace.line != 5
                match trace.expression:
                    Ast::Expr.Binary(left, TokenKind.EqEq, right, position):
                        continue if proof_ident_name(left) != "x"
                        match right:
                            Ast::Expr.IntLit(value, _):
                                continue if value != 9
                            _:
                                continue
                        return 2 if not source_gate(report, trace)
                        return 3 if source_gate(report, forged_trace(trace, trace.expression, 6, trace.kind, 0))
                        return 4 if source_gate(report, forged_trace(trace, trace.expression, 5, "local-binding", 0))
                        return 5 if source_gate(report, forged_trace(trace, trace.expression, 5, trace.kind, 1))
                        return 6 if source_gate(report, forged_trace(trace, Ast::Expr.Binary(left, TokenKind.EqEq, Ast::Expr.IntLit(8, position), position), 5, trace.kind, 0))
                        return 7 if source_gate(report, forged_trace(trace, Ast::Expr.Binary(Ast::Expr.Ident("evil", position), TokenKind.EqEq, right, position), 5, trace.kind, 0))
                        return 0
                    _:
                        pass
            99

def main() -> i64:
    text: sview = __SOURCE__
    bytes: mutable darray[u8] = []
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    audit(&report)
'''
harness = harness.replace("__SOURCE__", json.dumps(source))
# Reuse the original snapshot controls without modifying their source or assertions.
snapshot_module = ast.parse((ROOT / "scripts/tests/test_pop_snapshot_source.py").read_text())
snapshot = next(ast.literal_eval(n.value) for n in snapshot_module.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "HARNESS" for t in n.targets))
snapshot = snapshot.replace("../../Elisa-compiler/", str(FRONTEND.resolve()) + "/").replace("../src/", str(ROOT / "src") + "/")
with tempfile.TemporaryDirectory(prefix="pop-copy-source-") as temporary:
    for name, code in [("copied", harness), ("original_snapshot", snapshot)]:
        path = Path(temporary) / (name + ".elisa")
        binary = Path(temporary) / name
        path.write_text(code)
        subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
        subprocess.run([str(binary)], check=True, timeout=60)
print("pop copy: 8 certificates replayed; five forged trace controls and all original snapshot source controls pass")
