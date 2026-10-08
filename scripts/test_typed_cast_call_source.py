"""A builtin cast preserves payload call inputs; custom dispatch stays opaque."""
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
base = (ROOT / 'examples/widening_cast.elisa').read_text()
cast = '            wide: i64 = value.i64()'
source = base.replace(cast, cast + ' ' * 60)
owner_line = source.splitlines().index('def wide_first(tokens: Token) -> i64:') + 1
call_line = source.splitlines().index('            later: i64 = zero(rest)', owner_line) + 1

def replace_cast(text):
    old = cast + ' ' * 60
    new = ('            ' + text).ljust(len(old))
    assert len(old) == len(new)
    mutated = source.replace(old, new)
    # Every control must retain the later call's exact span, so an offset mismatch
    # cannot stand in for rejecting the changed dispatch or caller state.
    assert mutated.index('            later: i64 = zero(rest)', mutated.index('def wide_first')) == source.index('            later: i64 = zero(rest)', source.index('def wide_first'))
    return mutated

controls = {
    'source_alias': source + '\ntype u8 = i64\n',
    'target_alias': source + '\ntype i64 = u64\n',
    'custom_cast': source + '\ndef __cast__(value: u8) -> i64:\n    0\n',
    'numeric_method': source + '\ndef i64(value: u8) -> i64:\n    0\n',
    'noninteger_receiver': replace_cast('wide: i64 = rest.i64()'),
    'extra_argument': replace_cast('wide: i64 = value.i64(value)'),
    'compound_receiver': replace_cast('wide: i64 = (value + 0).i64()'),
    'unknown_selector': replace_cast('wide: i64 = value.other()'),
    'nested_method': replace_cast('wide: i64 = value.i64().i64()'),
    'write_capable_call': replace_cast('wide: i64 = steal(rest)') + '\ndef steal(tokens: mutable Token&) -> i64:\n    0\n',
    'payload_user_type': source.replace('value: u8, rest: Token', 'value: U8, rest: Token') + '\nstruct U8:\n    value: u8\n',
}
assert all(text != source for text in controls.values())
harness = prefix + r'''
extend ElisaProof:
    public:
        def summary_call(value: Ast::Expr) -> Ast::Expr:
            match value:
                Ast::Expr.Binary(call, TokenKind.EqEq, _, _):
                    return call if proof_replay_is_call(call)
                _:
                    pass
            Ast::Expr.Invalid

        def source_site(report: mutable ProofReport&, trace: ProofFactTrace, call: Ast::Expr) -> bool:
            report.replay_owner_line <- __OWNER_LINE__
            report.trace_owner_line <- __CALL_LINE__ + 1
            proof_replay_summary_direct_call_source_site(report, trace, call)

def parse_source(text: sview, bytes: mutable darray[u8]&, report: mutable ProofReport&) -> void:
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    proof_check(file, report)

def main() -> i64:
    original_bytes: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    parse_source(__SOURCE__, &original_bytes, &report)
    proof_replay_certificates(&report)
    return 1 if report.certificates.count != 36 or report.replay_gaps != 0
    for certificate in report.certificates:
        return 2 if not certificate.replayed
    for index in 0..<report.traces.records.count |report|:
        trace: ProofFactTrace = report.traces.records[index]
        continue if trace.name != "wide_first" or trace.line != __CALL_LINE__ or trace.kind != "function-summary"
        call: Ast::Expr = summary_call(trace.expression)
        continue if call is Ast::Expr.Invalid
        return 3 if not source_site(&report, trace, call)
        __CONTROLS__
        return 0
    return 99
'''
lines = []
for index, (name, text) in enumerate(controls.items(), 10):
    lines += [f'bytes_{index}: mutable darray[u8] = []',
              f'other_{index}: mutable ProofReport = proof_empty_report()',
              f'parse_source({json.dumps(text)}, &bytes_{index}, &other_{index})',
              f'return {index} if source_site(&other_{index}, trace, call)']
harness = harness.replace('__SOURCE__', json.dumps(source)).replace('__CONTROLS__', '\n        '.join(lines))
harness = harness.replace('__OWNER_LINE__', str(owner_line)).replace('__CALL_LINE__', str(call_line))
with tempfile.TemporaryDirectory(prefix='typed-cast-call-source-') as temporary:
    path = Path(temporary) / 'main.elisa'
    binary = Path(temporary) / 'gate'
    path.write_text(harness)
    subprocess.run([str(COMPILER / 'scripts/elisac_stage1.sh'), str(path), '-emit', 'exe', '-O0', '-o', str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print('typed cast call source: 36 certificates replayed; 11 dispatch/state controls refused at unchanged call spans')
