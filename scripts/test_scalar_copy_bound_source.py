"""Compile the independent copy-bound source gate with forged trace controls."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get('ELISA_COMPILER_ROOT', ROOT.parent / 'Elisa-compiler')).resolve()
FRONTEND = ROOT / 'build/snapshot/Elisa-compiler'
module = ast.parse((ROOT / 'scripts/test_loop_invariants_compile.py').read_text())
template = next(ast.literal_eval(node.value) for node in module.body
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'REPLAY_HARNESS' for t in node.targets))
prefix = template.split('extend ElisaProof:', 1)[0]
prefix = prefix.replace('../../Elisa-compiler/', str(FRONTEND.resolve()) + '/')
prefix = prefix.replace('../src/', str(ROOT / 'src') + '/')
source = (ROOT / 'test/repro/scalar_field_snapshot_bound.elisa').read_text()
harness = prefix + r'''
extend ElisaProof:
    public:
        def forged_trace(original: ProofFactTrace, expression: Ast::Expr, line: u32, kind: sview, summary: usize) -> ProofFactTrace:
            ProofFactTrace{expression: expression, kernel_expression: original.kernel_expression, kind: kind, line: line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: summary, owner_line: original.owner_line}

        def source_gate(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            report.replay_owner_line <- 4
            report.trace_owner_line <- 9
            proof_replay_scalar_copy_bound_source(report, trace)

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
        continue if candidate.kind != "proof-step" or candidate.line != 6
        match candidate.expression:
            Ast::Expr.Unary(TokenKind.Not, Ast::Expr.Binary(Ast::Expr.Ident(target, position), comparison, literal, inner_position), outer_position):
                continue if target != "slot"
                return 1 if not source_gate(&report, candidate)
                forged: mutable ProofFactTrace = candidate
                forged <- forged_trace(candidate, candidate.expression, 7, candidate.kind, 0)
                return 2 if source_gate(&report, forged)
                forged <- candidate
                forged <- forged_trace(candidate, Ast::Expr.Unary(TokenKind.Not, Ast::Expr.Binary(Ast::Expr.Ident(target, position), comparison, Ast::Expr.IntLit(5, inner_position), inner_position), outer_position), candidate.line, candidate.kind, 0)
                return 3 if source_gate(&report, forged)
                forged <- candidate
                forged <- forged_trace(candidate, Ast::Expr.Unary(TokenKind.Not, Ast::Expr.Binary(Ast::Expr.Ident("evil", position), comparison, literal, inner_position), outer_position), candidate.line, candidate.kind, 0)
                return 4 if source_gate(&report, forged)
                forged <- candidate
                forged <- forged_trace(candidate, candidate.expression, candidate.line, "local-binding", 0)
                return 5 if source_gate(&report, forged)
                forged <- candidate
                forged <- forged_trace(candidate, candidate.expression, candidate.line, candidate.kind, 1)
                return 6 if source_gate(&report, forged)
                alias_bytes: mutable darray[u8] = []
                alias_report: mutable ProofReport = proof_empty_report()
                parse_source(__ALIAS_SOURCE__, &alias_bytes, &alias_report)
                return 7 if source_gate(&alias_report, candidate)
                return 0
            _:
                pass
    return 8
'''
harness = harness.replace('__SOURCE__', json.dumps(source)).replace('__ALIAS_SOURCE__', json.dumps(source + '\ntype usize = i64\n'))
with tempfile.TemporaryDirectory(prefix='scalar-copy-bound-source-') as temp:
    path = Path(temp) / 'main.elisa'
    binary = Path(temp) / 'gate'
    path.write_text(harness)
    subprocess.run([str(COMPILER / 'scripts/elisac_stage1.sh'), str(path), '-emit', 'exe', '-O0', '-o', str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print('copy-bound source gate: authentic copy; wrong line/literal/local/kind/summary and primitive alias refused')
