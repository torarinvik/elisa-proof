"""Compile qualified statement constants and loop definition refusal controls."""
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
source = (ROOT / "examples/qualified_constants_statements.elisa").read_text()
harness = prefix + r'''
extend ElisaProof:
    public:
        def audit(report: mutable ProofReport&, changed: Ast::File&, shadowed: Ast::File&) -> i64:
            proof_replay_certificates(report)
            return 1 if report.certificates.count != 17
            for certificate in report.certificates |report|:
                return 2 if not certificate.replayed
            proof_replay_cache_fact_origins(report)
            loop_seen: mutable bool = false
            context_seen: mutable bool = false
            assignment_seen: mutable bool = false
            for index in 0..<report.certificates.count |report, changed, shadowed, loop_seen, context_seen, assignment_seen|:
                certificate: ProofGoalCertificate = report.certificates[index]
                continue if certificate.name != "looped" and certificate.name != "assigned"
                report.replay_owner_line <- 25 if certificate.name == "looped" else 13
                report.trace_owner_line <- certificate.line
                report.trace_consumer_certificate_index <- index + 1
                for offset in 0..<certificate.facts_count |report, certificate, changed, shadowed, loop_seen, context_seen, assignment_seen|:
                    trace_index: usize = report.traces.origin_indices[certificate.facts_start + offset]
                    continue if trace_index >= report.traces.records.count
                    trace: ProofFactTrace = report.traces.records[trace_index]
                    if (trace.kind == "loop-condition" or trace.kind == "loop-invariant") and certificate.line == 28:
                        context_seen <- true
                        return 3 if not proof_replay_local_binding_context_fact_source(report, trace, 28)
                        return 4 if proof_replay_local_binding_context_fact_source(report, trace, 29)
                        original: darray[Ast::Decl] = report.source_declarations
                        report.source_declarations <- changed.top_decls
                        return 5 if proof_replay_local_binding_context_fact_source(report, trace, 28)
                        report.source_declarations <- shadowed.top_decls
                        return 6 if proof_replay_local_binding_context_fact_source(report, trace, 28)
                        report.source_declarations <- original
                    if trace.kind == "local-binding" and trace.line == 17:
                        assignment_seen <- true
                        return 7 if not proof_replay_local_binding_mutable_local_source(report, trace, false)
                        original: darray[Ast::Decl] = report.source_declarations
                        report.source_declarations <- changed.top_decls
                        return 8 if proof_replay_local_binding_mutable_local_source(report, trace, false)
                        report.source_declarations <- original
                    if trace.kind == "local-binding" and trace.line == 32 and certificate.line == 28:
                        loop_seen <- true
                        return 9 if not proof_replay_local_binding_loop_self_update_source(report, trace, true)
                        return 10 if proof_replay_local_binding_loop_self_update_source(report, trace, false)
                        report.trace_owner_line <- 29
                        return 11 if proof_replay_local_binding_loop_self_update_source(report, trace, true)
                        report.trace_owner_line <- 28
                        result: i64 = definition_controls(report, trace, trace_index)
                        return result if result != 0
            return 17 if not loop_seen or not context_seen or not assignment_seen
            0

        def definition_controls(report: mutable ProofReport&, trace: ProofFactTrace, trace_index: usize) -> i64:
            match trace.expression:
                Ast::Expr.Binary(Ast::Expr.Ident(symbol, symbol_position), equation_operator, value, position):
                    return 18 if equation_operator != TokenKind.EqEq
                    return 12 if proof_replay_literal_rebind_unique(report, trace, symbol, symbol_position, value)
                    symbol_expression: Ast::Expr = Ast::Expr.Ident(symbol, symbol_position)
                    wrong_value: Ast::Expr = Ast::Expr.IntLit(2, position)
                    wrong_equation: Ast::Expr = Ast::Expr.Binary(symbol_expression, TokenKind.EqEq, wrong_value, position)
                    forged: ProofFactTrace = ProofFactTrace{expression: wrong_equation, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                    return 13 if proof_replay_local_binding_loop_self_update_source(report, forged, true)
                    original: ProofFactTrace = report.traces.records[trace_index]
                    report.traces.records[trace_index] <- forged
                    return 14 if proof_replay_rebind_definition_unique(report, trace, symbol, symbol_position, value, true)
                    report.traces.records[trace_index] <- original
                    return 15 if not proof_replay_local_binding_loop_self_update_source(report, trace, true)
                    alias_symbol: Ast::Expr = Ast::Expr.Ident("__elisa_rebind_63", symbol_position)
                    alias_equation: Ast::Expr = Ast::Expr.Binary(alias_symbol, TokenKind.EqEq, value, position)
                    alias: ProofFactTrace = ProofFactTrace{expression: alias_equation, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                    report.traces.records.push(alias)
                    return 19 if proof_replay_local_binding_loop_self_update_source(report, alias, true)
                    ignored: ProofFactTrace = report.traces.records.pop()
                _:
                    return 16
            0

def main() -> i64:
    text: sview = __SOURCE__
    changed_text: sview = __CHANGED__
    shadowed_text: sview = __SHADOWED__
    bytes: mutable darray[u8] = []
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    changed_bytes: mutable darray[u8] = []
    for index in 0..<sview_len(changed_text) |changed_bytes|:
        changed_bytes.push(sview_at(changed_text, index))
    changed_bytes.push(0)
    shadowed_bytes: mutable darray[u8] = []
    for index in 0..<sview_len(shadowed_text) |shadowed_bytes|:
        shadowed_bytes.push(sview_at(shadowed_text, index))
    shadowed_bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    changed: Ast::File = frontend_parse(&changed_bytes[0])
    shadowed: Ast::File = frontend_parse(&shadowed_bytes[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    audit(&report, changed, shadowed)
'''

harness = harness.replace("__SOURCE__", json.dumps(source)).replace("__CHANGED__", json.dumps(source.replace("const TOP: u8 = 10", "const TOP: u8 = 11"))).replace("__SHADOWED__", json.dumps(source.replace("def looped(x: u8)", "def looped(Limits: u8)")))
with tempfile.TemporaryDirectory(prefix="qualified-constant-source-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("qualified constant source: 17 certificates replayed; changed constant, shadowed module, wrong context/value and conflicting symbol refused")
