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
    baseline.replace("kept: u8 = keep(y + 1)", "kept: u8 = assigned(y + 1)"),
    baseline.replace("def keep(x: u8) -> u8", "def keep(x: u8) -> u16"),
    baseline.replace("kept: u8 = keep(y + 1)", "kept: u16 = keep(y + 1)"),
)
flow_skip_source = baseline.replace(
    "def looped(x: u8) -> u8:\n    requires x <= 5",
    "def looped(xs: darray[u8], x: u8) -> u8:\n    requires x <= 5 and 0 < xs.count")
flow_skip_source = flow_skip_source.replace(
    "decreases Limits::TOP - y", "skipped: u8 = get xs[0] else continue")
constants = "const LOOP_CANONICAL_SOURCE: sview = " + json.dumps(baseline) + "\n"
constants += "const LOOP_CANONICAL_MUTANTS: sview[12] = [" + ", ".join(map(json.dumps, mutants)) + "]\n"
constants += "const LOOP_CANONICAL_FLOW_SKIP_SOURCE: sview = " + json.dumps(flow_skip_source) + "\n"
harness = prefix + constants + r'''
extend ElisaProof:
    public:
        def proof_test_loop_result_symbol_bounds(report: mutable ProofReport&, certificate: ProofGoalCertificate, checked: mutable bool&) -> i64:
            result_symbol: mutable sview = ""
            result_symbol_position: mutable Ast::Pos = Ast::Pos{line: 0, column: 0, offset: 0, end_line: 0, end_column: 0, end_offset: 0}
            checked <- false
            for fact in 0..<certificate.facts_count |fact, certificate, report, result_symbol, result_symbol_position, checked|:
                origin: usize = report.traces.origin_indices[certificate.facts_start + fact]
                continue if origin >= report.traces.records.count
                trace: ProofFactTrace = report.traces.records[origin]
                continue if trace.kind != "type-bound"
                match trace.expression:
                    Ast::Expr.Call(Ast::Expr.Ident(marker, _), arguments, argument_names, position):
                        continue if marker != "__elisa_unsigned_type_bound" or arguments.count != 2 or argument_names.count != 0
                        match arguments[0]:
                            Ast::Expr.Ident(symbol, symbol_position):
                                continue if not proof_internal_name_is_rebind(symbol)
                                definition = proof_replay_result_symbol_definition(report, trace.name, symbol, symbol_position)
                                continue if not definition.known
                                return 216 if result_symbol != "" and result_symbol != symbol
                                result_symbol <- symbol
                                result_symbol_position <- symbol_position
                            _:
                                continue
                        return 208 if not proof_replay_type_bound_source_valid(report, trace)
                        saved_consumer_index: usize = report.trace_consumer_certificate_index
                        report.trace_consumer_certificate_index <- 0
                        no_context_accepted: bool = proof_replay_type_bound_source_valid(report, trace)
                        report.trace_consumer_certificate_index <- saved_consumer_index
                        return 234 if no_context_accepted
                        certificate_index: usize = saved_consumer_index - 1
                        # Keep the loop header/call lines stable while adding a GetElse continue
                        # before the call. The normal header preservation VC still has the call's
                        # result, but the continuation VC is tied to the transfer's own line.
                        flow_skip_bytes: mutable darray[u8] = []
                        proof_test_loop_replace_source(LOOP_CANONICAL_FLOW_SKIP_SOURCE, &flow_skip_bytes, &report)
                        flow_skip_accepted: bool = proof_replay_type_bound_source_valid(report, trace)
                        header_line: u32 = report.trace_owner_line
                        header_certificate_line: u32 = report.certificates[certificate_index].line
                        report.trace_owner_line <- 30
                        report.certificates[certificate_index].line <- 30
                        forged_continue_accepted: bool = proof_replay_type_bound_source_valid(report, trace)
                        report.trace_owner_line <- header_line
                        report.certificates[certificate_index].line <- header_certificate_line
                        proof_test_loop_replace_source(LOOP_CANONICAL_SOURCE, &flow_skip_bytes, &report)
                        return 238 if not flow_skip_accepted
                        return 239 if forged_continue_accepted
                        entry_goal_checked: mutable bool = false
                        for fact in 0..<certificate.facts_count |fact, certificate, report, trace, certificate_index, entry_goal_checked|:
                            origin: usize = report.traces.origin_indices[certificate.facts_start + fact]
                            continue if origin >= report.traces.records.count
                            context: ProofFactTrace = report.traces.records[origin]
                            continue if context.kind != "loop-invariant" or context.line != certificate.line
                            saved_goal: Ast::Expr = report.certificates[certificate_index].goal
                            report.certificates[certificate_index].goal <- context.expression
                            forged_entry_accepted: bool = proof_replay_type_bound_source_valid(report, trace)
                            report.certificates[certificate_index].goal <- saved_goal
                            entry_goal_checked <- true
                            return 235 if forged_entry_accepted
                            break
                        return 236 if not entry_goal_checked
                        alias_removed: mutable bool = false
                        for record_index in 0..<report.traces.records.count |record_index, report, trace, symbol, symbol_position, definition, alias_removed|:
                            candidate: ProofFactTrace = report.traces.records[record_index]
                            continue if candidate.kind != "local-binding" or candidate.name != trace.name or candidate.line != trace.line
                            match candidate.expression:
                                Ast::Expr.Binary(Ast::Expr.Ident(local, _), TokenKind.EqEq, Ast::Expr.Ident(value, value_position), _):
                                    continue if local != definition.local or value != symbol or not proof_replay_source_position_equal(value_position, symbol_position)
                                _:
                                    continue
                            detached: ProofFactTrace = ProofFactTrace{expression: candidate.expression, kernel_expression: candidate.kernel_expression, kind: "test-detached-local-binding", line: candidate.line, name: candidate.name, dependency: candidate.dependency, premises_start: candidate.premises_start, premises_count: candidate.premises_count, kernel_premises_start: candidate.kernel_premises_start, kernel_premises_count: candidate.kernel_premises_count, summary_bindings_start: candidate.summary_bindings_start, summary_bindings_count: candidate.summary_bindings_count, summary_requires_start: candidate.summary_requires_start, summary_requires_count: candidate.summary_requires_count, summary_ensure_index: candidate.summary_ensure_index, owner_line: candidate.owner_line}
                            report.traces.records[record_index] <- detached
                            alias_removed <- true
                        return 231 if not alias_removed
                        orphan_marker_accepted: bool = proof_replay_type_bound_source_valid(report, trace)
                        for record_index in 0..<report.traces.records.count |record_index, report, trace, symbol, symbol_position, definition|:
                            candidate: ProofFactTrace = report.traces.records[record_index]
                            continue if candidate.kind != "test-detached-local-binding" or candidate.name != trace.name or candidate.line != trace.line
                            match candidate.expression:
                                Ast::Expr.Binary(Ast::Expr.Ident(local, _), TokenKind.EqEq, Ast::Expr.Ident(value, value_position), _):
                                    continue if local != definition.local or value != symbol or not proof_replay_source_position_equal(value_position, symbol_position)
                                _:
                                    continue
                            restored: ProofFactTrace = ProofFactTrace{expression: candidate.expression, kernel_expression: candidate.kernel_expression, kind: "local-binding", line: candidate.line, name: candidate.name, dependency: candidate.dependency, premises_start: candidate.premises_start, premises_count: candidate.premises_count, kernel_premises_start: candidate.kernel_premises_start, kernel_premises_count: candidate.kernel_premises_count, summary_bindings_start: candidate.summary_bindings_start, summary_bindings_count: candidate.summary_bindings_count, summary_requires_start: candidate.summary_requires_start, summary_requires_count: candidate.summary_requires_count, summary_ensure_index: candidate.summary_ensure_index, owner_line: candidate.owner_line}
                            report.traces.records[record_index] <- restored
                        return 230 if orphan_marker_accepted
                        alias_line_shifted: mutable bool = false
                        for record_index in 0..<report.traces.records.count |record_index, report, trace, symbol, symbol_position, definition, alias_line_shifted|:
                            candidate: ProofFactTrace = report.traces.records[record_index]
                            continue if candidate.kind != "local-binding" or candidate.name != trace.name or candidate.line != trace.line
                            match candidate.expression:
                                Ast::Expr.Binary(Ast::Expr.Ident(local, _), TokenKind.EqEq, Ast::Expr.Ident(value, value_position), _):
                                    continue if local != definition.local or value != symbol or not proof_replay_source_position_equal(value_position, symbol_position)
                                _:
                                    continue
                            shifted_alias: ProofFactTrace = ProofFactTrace{expression: candidate.expression, kernel_expression: candidate.kernel_expression, kind: candidate.kind, line: candidate.line + 1, name: candidate.name, dependency: candidate.dependency, premises_start: candidate.premises_start, premises_count: candidate.premises_count, kernel_premises_start: candidate.kernel_premises_start, kernel_premises_count: candidate.kernel_premises_count, summary_bindings_start: candidate.summary_bindings_start, summary_bindings_count: candidate.summary_bindings_count, summary_requires_start: candidate.summary_requires_start, summary_requires_count: candidate.summary_requires_count, summary_ensure_index: candidate.summary_ensure_index, owner_line: candidate.owner_line}
                            report.traces.records[record_index] <- shifted_alias
                            alias_line_shifted <- true
                        return 233 if not alias_line_shifted
                        shifted_alias_accepted: bool = proof_replay_type_bound_source_valid(report, trace)
                        for record_index in 0..<report.traces.records.count |record_index, report, trace, symbol, symbol_position, definition|:
                            candidate: ProofFactTrace = report.traces.records[record_index]
                            continue if candidate.kind != "local-binding" or candidate.name != trace.name or candidate.line != trace.line + 1
                            match candidate.expression:
                                Ast::Expr.Binary(Ast::Expr.Ident(local, _), TokenKind.EqEq, Ast::Expr.Ident(value, value_position), _):
                                    continue if local != definition.local or value != symbol or not proof_replay_source_position_equal(value_position, symbol_position)
                                _:
                                    continue
                            restored: ProofFactTrace = ProofFactTrace{expression: candidate.expression, kernel_expression: candidate.kernel_expression, kind: candidate.kind, line: trace.line, name: candidate.name, dependency: candidate.dependency, premises_start: candidate.premises_start, premises_count: candidate.premises_count, kernel_premises_start: candidate.kernel_premises_start, kernel_premises_count: candidate.kernel_premises_count, summary_bindings_start: candidate.summary_bindings_start, summary_bindings_count: candidate.summary_bindings_count, summary_requires_start: candidate.summary_requires_start, summary_requires_count: candidate.summary_requires_count, summary_ensure_index: candidate.summary_ensure_index, owner_line: candidate.owner_line}
                            report.traces.records[record_index] <- restored
                        return 232 if shifted_alias_accepted
                        relabeled: ProofFactTrace = ProofFactTrace{expression: trace.expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line + 1, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                        return 228 if proof_replay_type_bound_source_valid(report, relabeled)
                        shifted_position: mutable Ast::Pos = symbol_position
                        shifted_position.column <- shifted_position.column + 1
                        shifted_position.offset <- shifted_position.offset + 1
                        shifted_arguments: darray[Ast::Expr] = [Ast::Expr.Ident(symbol, shifted_position), arguments[1]]
                        shifted_expression: Ast::Expr = Ast::Expr.Call(Ast::Expr.Ident(marker, position), shifted_arguments, argument_names, position)
                        shifted: ProofFactTrace = ProofFactTrace{expression: shifted_expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                        return 229 if proof_replay_type_bound_source_valid(report, shifted)
                        forged_arguments: darray[Ast::Expr] = [arguments[0], Ast::Expr.IntLit(16, position)]
                        forged_expression: Ast::Expr = Ast::Expr.Call(Ast::Expr.Ident(marker, position), forged_arguments, argument_names, position)
                        forged: ProofFactTrace = ProofFactTrace{expression: forged_expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                        return 209 if proof_replay_type_bound_source_valid(report, forged)
                    _:
                        pass
            return 0 if result_symbol == ""
            checked <- true
            lower_found: mutable bool = false
            upper_found: mutable bool = false
            forged_symbol: mutable sview = ""
            for symbol_index in 0..<PROOF_INTERNAL_REBIND_SYMBOL_COUNT |symbol_index, result_symbol, forged_symbol|:
                candidate_symbol: sview = proof_internal_rebind_name(symbol_index)
                if candidate_symbol != result_symbol:
                    forged_symbol <- candidate_symbol
                    break
            return 217 if forged_symbol == ""
            for fact in 0..<certificate.facts_count |fact, certificate, report, result_symbol, result_symbol_position, forged_symbol, lower_found, upper_found|:
                origin: usize = report.traces.origin_indices[certificate.facts_start + fact]
                continue if origin >= report.traces.records.count
                trace: ProofFactTrace = report.traces.records[origin]
                continue if trace.kind != "type-bound" or trace.line != result_symbol_position.line
                match trace.expression:
                    Ast::Expr.Binary(Ast::Expr.IntLit(0, position), TokenKind.LtEq, Ast::Expr.Ident(symbol, _), expression_position):
                        continue if symbol != result_symbol
                        lower_found <- true
                        return 206 if not proof_replay_type_bound_source_valid(report, trace)
                        forged_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.IntLit(0, position), TokenKind.LtEq, Ast::Expr.Ident(forged_symbol, position), expression_position)
                        forged: ProofFactTrace = ProofFactTrace{expression: forged_expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                        return 207 if proof_replay_type_bound_source_valid(report, forged)
                        stronger_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.IntLit(1, position), TokenKind.LtEq, Ast::Expr.Ident(symbol, position), expression_position)
                        stronger: ProofFactTrace = ProofFactTrace{expression: stronger_expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                        return 213 if proof_replay_type_bound_source_valid(report, stronger)
                    Ast::Expr.Binary(Ast::Expr.Ident(symbol, position), TokenKind.LtEq, Ast::Expr.IntLit(_, _), expression_position):
                        continue if symbol != result_symbol
                        upper_found <- true
                        return 210 if not proof_replay_type_bound_source_valid(report, trace)
                        forged_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(symbol, position), TokenKind.LtEq, Ast::Expr.IntLit(65535, position), expression_position)
                        forged: ProofFactTrace = ProofFactTrace{expression: forged_expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                        return 211 if proof_replay_type_bound_source_valid(report, forged)
                    _:
                        pass
            return 212 if not lower_found or not upper_found
            return 0

        def proof_test_loop_source_gate(report: mutable ProofReport&) -> i64 can Memory.Allocate, Abort.Panic:
            owner: mutable u32 = 0
            count: usize = report.certificates.count
            frames: mutable usize = 0
            result_bound_checks: mutable usize = 0
            for certificate_index in 0..<count |certificate_index, count, report, owner, frames, result_bound_checks|:
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
                result_symbol_checked: mutable bool = false
                result_symbol_gate: i64 = proof_test_loop_result_symbol_bounds(report, certificate, &result_symbol_checked)
                return result_symbol_gate if result_symbol_gate != 0
                result_bound_checks <- result_bound_checks + 1 if result_symbol_checked
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
            return 218 if result_bound_checks == 0
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
        bytes.push(text[index])
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report.source_declarations <- file.top_decls

def main() -> i64 can Memory.Allocate, Abort.Panic:
    original: mutable darray[u8] = []
    replaced: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(LOOP_CANONICAL_SOURCE, &original, &report)
    return 210 if report.failed != 0
    return 211 if report.certificates.count != 17
    if report.replay_gaps != 0:
        for index in 0..<report.certificates.count |index, report|:
            certificate: ProofGoalCertificate = report.certificates[index]
            return 220 + index.i64() if not certificate.replayed
        return 239
    initial_gate: i64 = proof_test_loop_source_gate(&report)
    return initial_gate if initial_gate != 0
    identity: i64 = proof_test_loop_identity_key(&report)
    return identity if identity != 0
    for index in 0..<12 |index, original, replaced, report|:
        proof_test_loop_replace_source(LOOP_CANONICAL_MUTANTS[index], &replaced, &report)
        source_gate: i64 = proof_test_loop_source_gate(&report)
        # Swapping to another declared u8 callee preserves the result-width witness, but its
        # precomputed function-summary must still fail during certificate replay below.
        return 212 if source_gate == 0 and index != 9
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
print("Loop canonical witnesses: 17 certificates replay; owner/site/type/input stay distinct; twelve stale sources refuse; normal-fallthrough and forged continue phases stay distinct")
