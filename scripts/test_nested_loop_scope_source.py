"""Compile nested lexical loop source reconstruction and refusal controls."""
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
source = (ROOT / "examples/loop_exit_frame.elisa").read_text()
harness = prefix + r'''
extend ElisaProof:
    public:
        def replay_gate(report: mutable ProofReport&) -> i64:
            proof_replay_certificates(report)
            return 1 if report.certificates.count != 9
            for certificate in report.certificates |report|:
                return 20 + certificate.line.i64() if not certificate.replayed
            0

        def audit(report: mutable ProofReport&) -> i64:
            body: mutable darray[Ast::Stmt] = []
            return 3 if not proof_replay_source_owner_body(report, "nested_outer_fact", 4, &body)
            condition: mutable Ast::Expr = Ast::Expr.Invalid
            inner: mutable darray[Ast::Stmt] = []
            lexical_body: mutable darray[Ast::Stmt] = []
            return 4 if not proof_replay_loop_scope(body, 10, &condition, &inner, &lexical_body)
            return 5 if proof_replay_loop_scope(body, 9, &condition, &inner, &lexical_body)
            matches: mutable usize = 0
            work: mutable usize = 4096
            return 6 if proof_replay_loop_scope_walk(body, 10, &condition, &inner, &lexical_body, &matches, &work, 0)
            work <- 0
            return 7 if proof_replay_loop_scope_walk(body, 10, &condition, &inner, &lexical_body, &matches, &work, 64)
            return 15 if not proof_replay_nested_local_unique(report.source_declarations, body, "k")
            duplicate_locals: mutable darray[Ast::Stmt] = []
            for statement in lexical_body |duplicate_locals|:
                match statement:
                    Ast::Stmt.VarDecl("k", _, _, _):
                        duplicate_locals.push(statement)
                        duplicate_locals.push(statement)
                    _:
                        pass
            return 16 if duplicate_locals.count != 2
            return 17 if proof_replay_nested_local_unique(report.source_declarations, duplicate_locals, "k")
            duplicates: mutable darray[Ast::Stmt] = []
            for statement in lexical_body |duplicates|:
                match statement:
                    Ast::Stmt.While(_, _, position):
                        if position.line == 10:
                            duplicates.push(statement)
                            duplicates.push(statement)
                    _:
                        pass
            return 8 if duplicates.count != 2
            return 9 if proof_replay_loop_scope(duplicates, 10, &condition, &inner, &lexical_body)
            proof_replay_cache_fact_origins(report)
            entry_seen: mutable bool = false
            preservation_seen: mutable bool = false
            for index in 0..<report.certificates.count |report, entry_seen, preservation_seen|:
                certificate: ProofGoalCertificate = report.certificates[index]
                continue if certificate.name != "nested_outer_fact" or certificate.line != 10
                report.replay_owner_line <- 4
                report.trace_owner_line <- 10
                report.trace_consumer_certificate_index <- index + 1
                for offset in 0..<certificate.facts_count |report, certificate, entry_seen, preservation_seen|:
                    trace_index: usize = report.traces.origin_indices[certificate.facts_start + offset]
                    continue if trace_index >= report.traces.records.count
                    trace: ProofFactTrace = report.traces.records[trace_index]
                    if trace.kind == "local-binding" and trace.line == 9:
                        entry_seen <- true
                        return 10 if not proof_replay_loop_entry_certificate(report, trace)
                    if trace.kind == "local-binding" and trace.line == 12:
                        preservation_seen <- true
                        return 11 if proof_replay_loop_entry_certificate(report, trace)
                        return 12 if proof_replay_local_binding_loop_self_update_source(report, trace, false)
                        return 13 if not proof_replay_local_binding_loop_self_update_source(report, trace, true)
            return 14 if not entry_seen or not preservation_seen
            0

def main() -> i64:
    text: sview = __SOURCE__
    bytes: mutable darray[u8] = []
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    result: i64 = replay_gate(&report)
    return result if result != 0
    audit(&report)
'''
harness = harness.replace("__SOURCE__", json.dumps(source))
with tempfile.TemporaryDirectory(prefix="nested-loop-source-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("nested loop source: 9 certificates replayed; unique lexical loop, budget, entry/preservation controls pass")
