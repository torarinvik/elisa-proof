"""Repeated loop checks share one typed source witness; stale contexts and forged names refuse."""
import ast
import json
import os
from pathlib import Path
from source_binding_harness_support import run_source_binding_replay_harness

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
prefix = next(ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "REPLAY_HARNESS"
                      for target in node.targets)).split("def main()")[0]
baseline = (ROOT / "examples/qualified_constants_statements.elisa").read_text()
mutants = (
    baseline.replace("TOP: u8 = 10", "TOP: u8 = 20"),
    baseline.replace("while y < Limits::TOP", "while y > Limits::TOP"),
    baseline.replace("invariant y <= Limits::TOP", "invariant y < Limits::TOP"),
    baseline.replace("y <- y + 1", "y <- y + 2"),
    baseline.replace("y <- y + 1", "y <- y - 1"),
    baseline.replace("def looped(x: u8)", "def looped(Limits: u8, x: u8)"),
    baseline.replace("const TOP: u8 = 10", "global mutable TOP: u8 = 10"),
    baseline.replace("while y < Limits::TOP", "while y < Other::TOP")
    + "\nconst module Other:\n    const TOP: u8 = 10\n",
    baseline.replace("def looped(x: u8)", "def looped(y: u8, x: u8)"),
)
constants = "const LOOP_CANONICAL_SOURCE: sview = " + json.dumps(baseline) + "\n"
constants += "const LOOP_CANONICAL_MUTANTS: sview[9] = [" + ", ".join(map(json.dumps, mutants)) + "]\n"
harness = prefix + constants + r'''
extend ElisaProof:
    public:
        def proof_test_loop_source_gate(report: mutable ProofReport&) -> i64 can Memory.Allocate, Abort.Panic:
            owner: mutable u32 = 0
            count: usize = report.certificates.count
            frames: mutable usize = 0
            for certificate_index in 0..<count |certificate_index, count, report, owner, frames|:
                certificate: ProofGoalCertificate = report.certificates[certificate_index]
                continue if certificate.name != "looped" or certificate.line != 28
                needed: mutable bool = false
                for fact in 0..<certificate.facts_count |fact, certificate, report, needed|:
                    origin: usize = report.traces.origin_indices[certificate.facts_start + fact]
                    continue if origin >= report.traces.records.count
                    trace: ProofFactTrace = report.traces.records[origin]
                    needed <- true if trace.kind == "local-binding" and trace.line == 32
                continue if not needed
                proof_replay_owner_function_line(report.source_declarations, certificate.name, certificate.line, &owner, 0)
                return 201 if owner == 0
                report.replay_owner_line <- owner
                report.trace_owner_line <- certificate.line
                report.trace_consumer_certificate_index <- certificate_index + 1
                contexts: mutable usize = 0
                updates: mutable usize = 0
                for fact in 0..<certificate.facts_count |fact, certificate, report, contexts, updates|:
                    origin: usize = report.traces.origin_indices[certificate.facts_start + fact]
                    continue if origin >= report.traces.records.count
                    trace: ProofFactTrace = report.traces.records[origin]
                    if trace.kind == "loop-condition" or trace.kind == "loop-invariant":
                        return 202 if not proof_replay_local_binding_context_fact_source(report, trace, certificate.line)
                        contexts <- contexts + 1
                    if trace.kind == "local-binding" and trace.line == 32:
                        return 203 if not proof_replay_local_binding_loop_self_update_source(report, trace, true)
                        updates <- updates + 1
                if updates > 0:
                    return 204 if contexts < 2
                    frames <- frames + 1
            return 0 if frames == 3 else 205

        def proof_test_loop_identity_key(report: mutable ProofReport&) -> i64:
            count: usize = report.traces.records.count
            for index in 0..<count |index, count, report|:
                trace: ProofFactTrace = report.traces.records[index]
                continue if trace.kind != "local-binding" or trace.name != "looped" or trace.line != 32
                match trace.expression:
                    Ast::Expr.Binary(Ast::Expr.Ident(symbol, position), TokenKind.EqEq, value, _):
                        prior: usize = report.rebind_symbols
                        same: sview = proof_unsigned_rebind_symbol(report, "looped", 8, value, position)
                        return 220 if same != symbol or report.rebind_symbols != prior
                        return 221 if proof_unsigned_rebind_existing_symbol(report, "looped", 16, value, position) != ""
                        return 222 if proof_unsigned_rebind_existing_symbol(report, "keep", 8, value, position) != ""
                        shifted: mutable Ast::Pos = position
                        shifted.offset <- position.offset + 1
                        return 223 if proof_unsigned_rebind_existing_symbol(report, "looped", 8, value, shifted) != ""
                        match value:
                            Ast::Expr.Binary(left, operator, _, value_position):
                                changed: Ast::Expr = Ast::Expr.Binary(left, operator, Ast::Expr.IntLit(2, value_position), value_position)
                                return 224 if proof_unsigned_rebind_existing_symbol(report, "looped", 8, changed, position) != ""
                                different_input: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("other", value_position), operator, Ast::Expr.IntLit(1, value_position), value_position)
                                return 225 if proof_unsigned_rebind_existing_symbol(report, "looped", 8, different_input, position) != ""
                            _:
                                return 226
                        return 0
                    _:
                        pass
            return 227

def proof_test_loop_replace_source(text: sview, bytes: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    bytes.clear()
    for index in 0..<sview_len(text) |index, text, bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report.source_declarations <- file.top_decls

def main() -> i64 can Memory.Allocate, Abort.Panic:
    original: mutable darray[u8] = []
    replaced: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(LOOP_CANONICAL_SOURCE, &original, &report)
    return 210 if report.failed != 0 or report.certificates.count != 17 or report.replay_gaps != 0
    initial_gate: i64 = proof_test_loop_source_gate(&report)
    return initial_gate if initial_gate != 0
    identity: i64 = proof_test_loop_identity_key(&report)
    return identity if identity != 0
    for index in 0..<9 |index, original, replaced, report|:
        proof_test_loop_replace_source(LOOP_CANONICAL_MUTANTS[index], &replaced, &report)
        return 212 if proof_test_loop_source_gate(&report) == 0
        proof_replay_certificates(&report)
        return 213 if report.replay_gaps == 0
        proof_test_loop_replace_source(LOOP_CANONICAL_SOURCE, &replaced, &report)
        return 214 if proof_test_loop_source_gate(&report) != 0
        proof_replay_certificates(&report)
        return 215 if report.replay_gaps != 0
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Loop canonical witnesses: 17 certificates replay; owner/site/type/input stay distinct; nine stale sources refuse and restore")
