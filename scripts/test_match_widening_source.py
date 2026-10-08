"""Authenticate payload widening equations against exact source match arms."""
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
source = (ROOT / 'examples/widening_cast.elisa').read_text()
owner_line = source.splitlines().index('def wide_first(tokens: Token) -> i64:') + 1
cast_line = source.splitlines().index('            wide: i64 = value.i64()') + 1
consumer_line = source.splitlines().index('            return wide + later') + 1
harness = prefix + r'''
extend ElisaProof:
    public:
        def source_gate(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            report.replay_owner_line <- __OWNER_LINE__
            report.trace_owner_line <- __CONSUMER_LINE__
            proof_replay_local_binding_widening_cast_declaration_source(report, trace)

        def replace_expression(trace: ProofFactTrace, expression: Ast::Expr, line: u32) -> ProofFactTrace:
            ProofFactTrace{expression: expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}

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
        trace: ProofFactTrace = report.traces.records[index]
        continue if trace.name != "wide_first" or trace.line != __CAST_LINE__ or trace.kind != "proof-step"
        match trace.expression:
            Ast::Expr.Binary(Ast::Expr.Ident("wide", target_position), TokenKind.EqEq, Ast::Expr.Ident("__elisa_rebind_0", receiver_position), position):
                return 1 if not source_gate(&report, trace)
                return 2 if source_gate(&report, replace_expression(trace, trace.expression, trace.line + 1))
                wrong_receiver: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("wide", target_position), TokenKind.EqEq, Ast::Expr.Ident("__elisa_rebind_1", receiver_position), position)
                return 3 if source_gate(&report, replace_expression(trace, wrong_receiver, trace.line))
                wrong_target: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("later", target_position), TokenKind.EqEq, Ast::Expr.Ident("__elisa_rebind_0", receiver_position), position)
                return 4 if source_gate(&report, replace_expression(trace, wrong_target, trace.line))
                __CONTROLS__
                return 0
            _:
                pass
    return 99
'''
controls = {
    'narrowing': source.replace('wide: i64 = value.i64()', 'wide: i8 = value.i8()'),
    'mutable_target': source.replace('wide: i64 = value.i64()', 'wide: mutable i64 = value.i64()'),
    'wrong_method': source.replace('wide: i64 = value.i64()', 'wide: i64 = value.u64()'),
    'wrong_payload': source.replace('wide: i64 = value.i64()', 'wide: i64 = rest.i64()'),
    'payload_shadow': source.replace('wide: i64 = value.i64()', 'value: u8 = 0\n            wide: i64 = value.i64()'),
    'payload_write': source.replace('wide: i64 = value.i64()', 'wide: i64 = value.i64()\n            value <- 0'),
    'mutable_subject': source.replace('def wide_first(tokens: Token)', 'def wide_first(tokens: mutable Token)'),
    'earlier_witness': source.replace('def wide_first(tokens: Token) -> i64:\n    ensure result >= 0', 'def wide_first(tokens: Token) -> i64:\n    earlier: mutable u8 = 0\n    ensure result >= 0'),
    'wrong_return_path': source.replace('return wide + later', 'if later == 0:\n                return wide\n            return later'),
}
lines = []
for index, (name, text) in enumerate(controls.items(), 10):
    assert text != source, name
    lines += [f'other_{index}: mutable ProofReport = proof_empty_report()',
              f'parse_source({json.dumps(text)}, &bytes, &other_{index})',
              f'return {index} if source_gate(&other_{index}, trace)']
harness = harness.replace('__SOURCE__', json.dumps(source)).replace('__CONTROLS__', '\n                '.join(lines))
for marker, value in [('__OWNER_LINE__', owner_line), ('__CAST_LINE__', cast_line), ('__CONSUMER_LINE__', consumer_line)]:
    harness = harness.replace(marker, str(value))
with tempfile.TemporaryDirectory(prefix='match-widening-source-') as temporary:
    path = Path(temporary) / 'main.elisa'
    binary = Path(temporary) / 'gate'
    path.write_text(harness)
    subprocess.run([str(COMPILER / 'scripts/elisac_stage1.sh'), str(path), '-emit', 'exe', '-O0', '-o', str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print('match widening: authentic payload equation accepted; 12 forged trace/source controls refused')
