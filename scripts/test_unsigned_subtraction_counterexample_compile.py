"""Compile exact unsigned subtraction diagnostic controls and the original branch fixture."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get('ELISA_COMPILER_ROOT', ROOT.parent / 'Elisa-compiler')).resolve()
FRONTEND = Path(os.environ.get('ELISA_PROOF_FRONTEND_ROOT', ROOT / 'build/snapshot/Elisa-compiler')).resolve()
module = ast.parse((ROOT / 'scripts/test_loop_invariants_compile.py').read_text())
template = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'REPLAY_HARNESS' for target in node.targets))
prefix = template.split('extend ElisaProof:', 1)[0]
prefix = prefix.replace('../../Elisa-compiler/', str(FRONTEND) + '/').replace('../src/', str(ROOT / 'src') + '/')
harness = prefix + r'''
extend ElisaProof:
    public:
        def unsigned_subtraction_gate() -> i64:
            position: Ast::Pos = Ast::Pos{line: 1, column: 1, offset: 0, end_line: 1, end_column: 1, end_offset: 0}
            a: Ast::Expr = Ast::Expr.Ident("a", position)
            b: Ast::Expr = Ast::Expr.Ident("b", position)
            expression: Ast::Expr = Ast::Expr.Binary(a, TokenKind.Minus, b, position)
            names: darray[sview] = ["a", "b"]
            positive_values: darray[i64] = [15, 10]
            zero_values: darray[i64] = [15, 15]
            underflow_values: darray[i64] = [10, 15]
            invalid_values: darray[i64] = [-1, 0]
            outside_values: darray[i64] = [256, 0]
            annotations: darray[Ast::EnumAnnotation] = []
            for width in [8, 16, 32] |position, a, b, expression, names, annotations, positive_values, zero_values, underflow_values, invalid_values, outside_values|:
                marker: Ast::Expr = Ast::Expr.Ident("__elisa_unsigned_type_bound", position)
                facts: darray[Ast::Expr] = [Ast::Expr.Call(marker, [a, Ast::Expr.IntLit(width, position)], [], position), Ast::Expr.Call(marker, [b, Ast::Expr.IntLit(width, position)], [], position)]
                positive = proof_counterexample_machine_int(expression, names, positive_values, facts, annotations, 0)
                return 1 if not positive.known or not positive.unsigned or positive.width != width or positive.value != 5
                zero = proof_counterexample_machine_int(expression, names, zero_values, facts, annotations, 0)
                return 2 if not zero.known or zero.value != 0
                return 3 if proof_counterexample_machine_int(expression, names, underflow_values, facts, annotations, 0).known
                return 4 if proof_counterexample_machine_int(expression, names, invalid_values, facts, annotations, 0).known
                return 7 if proof_counterexample_machine_int(expression, names, positive_values, facts, annotations, 64).known
                if width == 8:
                    return 8 if proof_counterexample_machine_int(expression, names, outside_values, facts, annotations, 0).known
                report: mutable ProofReport = proof_empty_report()
                goal: Ast::Expr = Ast::Expr.Binary(expression, TokenKind.Lt, Ast::Expr.IntLit(0, position), position)
                sub_rows: mutable darray[Ast::EnumAnnotation] = []
                sub_rows.push(Ast::EnumAnnotation{owner: "__impl_concrete", name: "u8", line: 1})
                sub_rows.push(Ast::EnumAnnotation{owner: "__impl_scope", name: "Sub", line: 1})
                report.source_annotations <- sub_rows
                return 9 if proof_counterexample_fragment(goal, facts, report, "audit", 0)
                ord_rows: mutable darray[Ast::EnumAnnotation] = []
                ord_rows.push(Ast::EnumAnnotation{owner: "__impl_concrete", name: "u8", line: 1})
                ord_rows.push(Ast::EnumAnnotation{owner: "__impl_scope", name: "Ord", line: 1})
                report.source_annotations <- ord_rows
                return 13 if proof_counterexample_fragment(goal, facts, report, "audit", 0)
                mixed: darray[Ast::Expr] = [facts[0], Ast::Expr.Call(marker, [b, Ast::Expr.IntLit(64, position)], [], position)]
                return 5 if proof_counterexample_machine_int(expression, names, positive_values, mixed, annotations, 0).known
            facts: darray[Ast::Expr] = []
            return 6 if proof_counterexample_machine_int(expression, names, positive_values, facts, annotations, 0).known
            0

        def branch_gate(report: mutable ProofReport&) -> i64:
            proof_replay_certificates(report)
            return 10 if report.certificates.count != 23 or report.replay_gaps != 0
            for finding in report.findings:
                if finding.name == "subtraction_path_strict_negative":
                    return 11 if finding.status != "disproved" or not finding.counterexample_found
                    return 0
            12

def main() -> i64:
    direct: i64 = unsigned_subtraction_gate()
    return direct if direct != 0
    text: sview = __SOURCE__
    bytes: mutable darray[u8] = []
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    branch_gate(&report)
'''
harness = harness.replace('__SOURCE__', json.dumps((ROOT / 'examples/return_branch_path_fact.elisa').read_text()))
with tempfile.TemporaryDirectory(prefix='unsigned-subtraction-counterexample-') as temporary:
    path = Path(temporary) / 'main.elisa'
    binary = Path(temporary) / 'gate'
    path.write_text(harness)
    subprocess.run([str(COMPILER / 'scripts/elisac_stage1.sh'), str(path), '-emit', 'exe', '-O0', '-o', str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print('unsigned subtraction: exact typed diagnostics; underflow, mixed widths and untyped names refused; branch negatives disproved')
