"""Compile the source-level producer/replay probe with the freshness-checked Stage1 toolchain.

This deliberately does not execute build/elisa-proof or build/elisa-proof-replay: they can be
from different source snapshots. The temporary Elisa executable includes the current checker
and replay modules directly, then forges in-memory function-summary and deterministic-call traces.
"""

from pathlib import Path
import os
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
STAGE1_WRAPPER = COMPILER_ROOT / "scripts" / "elisac_stage1.sh"
FRESHNESS_CHECK = COMPILER_ROOT / "scripts" / "assert_stage1_fresh.sh"


HARNESS = r'''include "../../Elisa-compiler/elisacore_std/elisacore_runtime_prelude.elisa"
include "../../Elisa-compiler/elisacore_std/collections.elisa"
include "../../Elisa-compiler/elisacore_std/elisacore_runtime_strings.elisa"
include "../../Elisa-compiler/src/semantic/semantic.elisa"
include "../src/proof/kernel_core.elisa"
include "../src/proof/operator_impl_model.elisa"
include "../src/proof/model/enum_index.elisa"
include "../src/proof/model/findings.elisa"
include "../src/proof/model.elisa"
include "../src/proof/model/lemma_table.elisa"
include "../src/proof/model/report_invariants.elisa"
include "../src/proof/kernel.elisa"
include "../src/proof/kernel_intern.elisa"
include "../src/proof/expr.elisa"
include "../src/proof/linear.elisa"
include "../src/proof/resources.elisa"
include "../src/proof/check.elisa"
include "../src/proof/kernel_replay.elisa"
include "../src/proof/replay.elisa"
include "../src/proof/tactics.elisa"

extend ElisaProof:
    public:
        # The alias is consumed by the certificate at the `return` that reads the local.
        def test_summary_local_binding_source(report: mutable ProofReport&, owner: sview, owner_line: u32, local_name: sview, binding_position: Ast::Pos, call: Ast::Expr) -> bool:
            saved_owner_line: u32 = report.replay_owner_line
            saved_consumer_line: u32 = report.trace_owner_line
            report.replay_owner_line <- owner_line
            report.trace_owner_line <- binding_position.line
            valid: bool = proof_replay_summary_local_alias_valid(report, owner, local_name, binding_position, call)
            report.replay_owner_line <- saved_owner_line
            report.trace_owner_line <- saved_consumer_line
            return valid

        def test_summary_argument_order_replay() -> bool:
            report: mutable ProofReport = proof_empty_report()
            report.executables.parameters.push("first")
            report.executables.parameters.push("second")
            report.traces.summary_names.push("first")
            report.traces.summary_names.push("second")
            position: Ast::Pos = Ast::pos_at_line(1)
            report.traces.summary_values.push(Ast::Expr.Ident("left", position))
            report.traces.summary_values.push(Ast::Expr.Ident("right", position))
            summary: ProofExecutableSummary = ProofExecutableSummary{name: "ordered", line: 1, parameters_start: 0, parameters_count: 2, requires_start: 0, requires_count: 0, ensures_start: 0, ensures_count: 0, pure: true, verified: true, verification_reason: ""}
            trace: ProofFactTrace = ProofFactTrace{expression: Ast::Expr.Absent, kernel_expression: 0, kind: "function-summary", line: 1, name: "caller", dependency: "ordered", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 3, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 1}
            arguments: darray[Ast::Expr] = [Ast::Expr.Ident("left", position), Ast::Expr.Ident("right", position)]
            argument_names: darray[sview] = ["", ""]
            call: Ast::Expr = Ast::Expr.Call(Ast::Expr.Ident("ordered", position), arguments, argument_names, position)
            return false if not proof_replay_summary_call_arguments_match(&report, trace, summary, call)
            report.traces.summary_values[0] <- Ast::Expr.Ident("right", position)
            report.traces.summary_values[1] <- Ast::Expr.Ident("left", position)
            return not proof_replay_summary_call_arguments_match(&report, trace, summary, call)

        def test_summary_source_call_known(report: ProofReport&, trace: ProofFactTrace, summary: ProofExecutableSummary) -> bool:
            return proof_replay_summary_source_call(report, trace, summary).known

        def test_summary_source_call(report: ProofReport&, trace: ProofFactTrace, summary: ProofExecutableSummary) -> (known: bool, call: Ast::Expr):
            return proof_replay_summary_source_call(report, trace, summary)

        def test_deterministic_source_call_site(report: ProofReport&, trace: ProofFactTrace, call: Ast::Expr) -> bool:
            return proof_replay_deterministic_call_source_site(report, trace, call)

        def test_deterministic_source_call_matches(report: ProofReport&, trace: ProofFactTrace, call: Ast::Expr) -> (known: bool, matches: usize):
            matches: mutable usize = 0
            owner_line: mutable u32 = report.replay_owner_line
            owner_line <- 0 if owner_line == 4294967295
            known: bool = proof_replay_deterministic_call_source_declarations(report.source_declarations, trace.name, owner_line, call, trace.line, &matches, 0)
            return (known, matches)

        def test_deterministic_source_contains(report: ProofReport&, owner: sview, call: Ast::Expr) -> bool:
            for declaration in report.source_declarations |declaration, owner, call|:
                match declaration:
                    Ast::Decl.Func(name, _, _, body, _, _, _) if name == owner:
                        for statement in body |statement, call|:
                            match statement:
                                Ast::Stmt.VarDecl(_, _, expression, _):
                                    return proof_replay_deterministic_call_source_contains(expression, call, 0)
                                _:
                                    pass
                    _:
                        pass
            return false

        def test_local_return_position(body: darray[Ast::Stmt]&, local_name: sview, position: mutable Ast::Pos&, found: mutable bool&) -> bool:
            for statement in body |local_name, position, found|:
                match statement:
                    Ast::Stmt.Return(value, _):
                        match value:
                            Ast::Expr.Ident(name, source_position) if name == local_name:
                                position <- source_position
                                found <- true
                    _:
                        pass
            return true

        def test_local_return_position_declarations(declarations: darray[Ast::Decl]&, owner: sview, owner_line: u32, local_name: sview, position: mutable Ast::Pos&, found: mutable bool&, depth: usize) -> bool:
            return false if depth >= 96
            for declaration in declarations |owner, owner_line, local_name, position, found, depth|:
                match declaration:
                    Ast::Decl.Func(name, _, _, body, _, _, function_position):
                        if name == owner and function_position.line == owner_line:
                            return test_local_return_position(body, local_name, position, found)
                    Ast::Decl.Module(_, nested, _) | Ast::Decl.Scoped(nested, _):
                        return false if not test_local_return_position_declarations(nested, owner, owner_line, local_name, position, found, depth + 1)
                    _:
                        pass
            return true

using Ast
using ElisaProof

const FORGED_LOCAL_BINDING_VALUE: i64 = 987654321
const FORGED_LOCAL_BINDING_ENCODING_FAILED: i64 = 25
const FORGED_LOCAL_BINDING_ACCEPTED: i64 = 26
const SCOPED_CALLER_SOURCE_LINE: u32 = 32

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    return 34 if not test_summary_argument_order_replay()
    text: sview = "module Gate:\n    module Inner:\n        public:\n            def bounded(x: i64) -> i64:\n                requires x >= 0\n                ensure result >= 0\n                return x\n\nmodule Elsewhere:\n    module Inner:\n        public:\n            def unrelated(x: i64) -> i64:\n                return x\n\ndef caller(x: i64) -> i64:\n    requires x >= 0\n    ensure result >= 0\n    return Gate::Inner::bounded(x)\n\ndef caller_local(x: i64) -> i64:\n    requires x >= 0\n    ensure result >= 0\n    result_value: i64 = Gate::Inner::bounded(x)\n    return result_value\n\ndef caller_guard(x: i64) -> i64:\n    requires x >= 0\n    ensure result >= 0\n    return 1 if Gate::Inner::bounded(x) < 0\n    return 0\n\ndef caller_scoped(x: i64) -> i64:\n    requires x >= 0\n    ensure result >= 0\n    result_value: i64 =\n        Gate::Inner::bounded(x)\n    return result_value\n"
    source: mutable darray[u8] = []
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    proof_replay_certificates(&report)

    scoped_trace_index: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, scoped_trace_index|:
        candidate: ProofFactTrace = report.traces.records[index]
        if candidate.kind == "function-summary" and candidate.name == "caller_scoped" and candidate.dependency == "bounded":
            scoped_trace_index <- index
            break
    return 45 if scoped_trace_index >= report.traces.records.count
    scoped_trace: mutable ProofFactTrace = report.traces.records[scoped_trace_index]
    scoped_call_index: usize = scoped_trace.summary_bindings_start + scoped_trace.summary_bindings_count - 1
    return 46 if scoped_call_index >= report.traces.summary_values.count
    scoped_call: Ast::Expr = report.traces.summary_values[scoped_call_index]
    return 49 if Ast::expr_pos(scoped_call).line != scoped_trace.line
    return 52 if not test_deterministic_source_contains(&report, scoped_trace.name, scoped_call)
    report.replay_owner_line <- SCOPED_CALLER_SOURCE_LINE
    source_site_status: (known: bool, matches: usize) = test_deterministic_source_call_matches(&report, scoped_trace, scoped_call)
    return 50 if not source_site_status.known
    return 51 if source_site_status.matches != 1
    return 47 if not test_deterministic_source_call_site(&report, scoped_trace, scoped_call)
    wrong_scoped_owner: ProofFactTrace = ProofFactTrace{expression: scoped_trace.expression, kernel_expression: scoped_trace.kernel_expression, kind: scoped_trace.kind, line: scoped_trace.line, name: "caller", dependency: scoped_trace.dependency, premises_start: scoped_trace.premises_start, premises_count: scoped_trace.premises_count, kernel_premises_start: scoped_trace.kernel_premises_start, kernel_premises_count: scoped_trace.kernel_premises_count, summary_bindings_start: scoped_trace.summary_bindings_start, summary_bindings_count: scoped_trace.summary_bindings_count, summary_requires_start: scoped_trace.summary_requires_start, summary_requires_count: scoped_trace.summary_requires_count, summary_ensure_index: scoped_trace.summary_ensure_index, owner_line: scoped_trace.owner_line}
    return 48 if test_deterministic_source_call_site(&report, wrong_scoped_owner, scoped_call)
    report.replay_owner_line <- 0

    summary_index: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, summary_index|:
        if report.traces.records[index].kind == "function-summary" and report.traces.records[index].name == "caller" and report.traces.records[index].dependency == "bounded":
            summary_index <- index
            break
    return 9 if summary_index >= report.traces.records.count
    summary_original: ProofFactTrace = report.traces.records[summary_index]
    return 10 if not proof_replay_fact_trace_entry(&report, summary_index)

    guard_trace_index: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, guard_trace_index|:
        candidate: ProofFactTrace = report.traces.records[index]
        if candidate.kind == "function-summary" and candidate.name == "caller_guard" and candidate.dependency == "bounded":
            guard_trace_index <- index
            break
    return 43 if guard_trace_index >= report.traces.records.count
    report.replay_owner_line <- 26
    return 44 if not proof_replay_fact_trace_entry(&report, guard_trace_index)
    report.replay_owner_line <- 15
    summary_result_index: mutable usize = summary_original.summary_bindings_start
    for offset in 0..<summary_original.summary_bindings_count |offset, summary_original, report, summary_result_index|:
        summary_result_index <- summary_original.summary_bindings_start + offset if report.traces.summary_names[summary_original.summary_bindings_start + offset] == "result"
    return 11 if summary_result_index == summary_original.summary_bindings_start
    summary_result_original: Ast::Expr = report.traces.summary_values[summary_result_index]
    forged_summary_result: mutable Ast::Expr = Ast::Expr.Invalid
    match summary_result_original:
        Ast::Expr.Call(_, call_arguments, call_names, call_position):
            wrong_module: Ast::Expr = Ast::Expr.Scope(Ast::Expr.Ident("Elsewhere", call_position), "Inner", call_position)
            forged_callee: Ast::Expr = Ast::Expr.Scope(wrong_module, "bounded", call_position)
            forged_summary_result <- Ast::Expr.Call(forged_callee, call_arguments, call_names, call_position)
        _:
            return 15
    forged_owner_summary: Ast::Expr = Ast::Expr.Binary(forged_summary_result, TokenKind.GtEq, Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression)), Ast::expr_pos(summary_original.expression))
    forged_owner_encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_owner_summary, &report, summary_original.name)
    return 16 if not forged_owner_encoded.known
    report.traces.summary_values[summary_result_index] <- forged_summary_result
    report.traces.records[summary_index] <- ProofFactTrace{expression: forged_owner_summary, kernel_expression: forged_owner_encoded.root, kind: summary_original.kind, line: summary_original.line, name: summary_original.name, dependency: summary_original.dependency, premises_start: summary_original.premises_start, premises_count: summary_original.premises_count, kernel_premises_start: summary_original.kernel_premises_start, kernel_premises_count: summary_original.kernel_premises_count, summary_bindings_start: summary_original.summary_bindings_start, summary_bindings_count: summary_original.summary_bindings_count, summary_requires_start: summary_original.summary_requires_start, summary_requires_count: summary_original.summary_requires_count, summary_ensure_index: summary_original.summary_ensure_index, owner_line: summary_original.owner_line}
    return 17 if proof_replay_fact_trace_entry(&report, summary_index)
    report.traces.records[summary_index] <- summary_original
    report.traces.summary_values[summary_result_index] <- summary_result_original
    return 18 if not proof_replay_fact_trace_entry(&report, summary_index)

    report.traces.summary_values[summary_result_index] <- Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression))
    forged_summary: Ast::Expr = Ast::Expr.Binary(Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression)), TokenKind.GtEq, Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression)), Ast::expr_pos(summary_original.expression))
    summary_encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_summary, &report, summary_original.name)
    return 12 if not summary_encoded.known
    report.traces.records[summary_index] <- ProofFactTrace{expression: forged_summary, kernel_expression: summary_encoded.root, kind: summary_original.kind, line: summary_original.line, name: summary_original.name, dependency: summary_original.dependency, premises_start: summary_original.premises_start, premises_count: summary_original.premises_count, kernel_premises_start: summary_original.kernel_premises_start, kernel_premises_count: summary_original.kernel_premises_count, summary_bindings_start: summary_original.summary_bindings_start, summary_bindings_count: summary_original.summary_bindings_count, summary_requires_start: summary_original.summary_requires_start, summary_requires_count: summary_original.summary_requires_count, summary_ensure_index: summary_original.summary_ensure_index, owner_line: summary_original.owner_line}
    return 13 if proof_replay_fact_trace_entry(&report, summary_index)
    report.traces.records[summary_index] <- summary_original
    report.traces.summary_values[summary_result_index] <- summary_result_original
    return 14 if not proof_replay_fact_trace_entry(&report, summary_index)

    local_trace_index: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, local_trace_index|:
        candidate: ProofFactTrace = report.traces.records[index]
        continue if candidate.kind != "function-summary" or candidate.name != "caller_local" or candidate.dependency != "bounded"
        local_trace_index <- index
    return 19 if local_trace_index >= report.traces.records.count
    local_trace: ProofFactTrace = report.traces.records[local_trace_index]
    local_result_index: usize = local_trace.summary_bindings_start + 1
    return 20 if local_result_index >= report.traces.summary_values.count
    local_call: mutable Ast::Expr = report.traces.summary_values[local_result_index]
    match local_call:
        Ast::Expr.Paren(inner, _):
            local_call <- inner
        _:
            pass
    local_binding_position: mutable Ast::Pos = Ast::pos_at_line(24)
    local_binding_found: mutable bool = false
    return 21 if not test_local_return_position_declarations(report.source_declarations, "caller_local", 20, "result_value", &local_binding_position, &local_binding_found, 0)
    return 22 if not local_binding_found
    return 23 if not test_summary_local_binding_source(&report, "caller_local", 20, "result_value", local_binding_position, local_call)
    return 24 if test_summary_local_binding_source(&report, "caller_local", 20, "wrong_local", local_binding_position, local_call)
    summary_argument_index: usize = summary_original.summary_bindings_start
    summary_argument_original: Ast::Expr = report.traces.summary_values[summary_argument_index]
    report.traces.summary_values[summary_argument_index] <- Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression))
    return 25 if proof_replay_fact_trace_entry(&report, summary_index)
    report.traces.summary_values[summary_argument_index] <- summary_argument_original
    return 26 if not proof_replay_fact_trace_entry(&report, summary_index)

    assignment_text: sview = "def assignment_add_one(x: i64) -> i64:\n    requires x >= 0\n    ensure result == x + 1\n    return x + 1\n\ndef assignment_rhs_state(x: i64) -> i64:\n    requires x >= 0\n    ensure result == x + 1\n    value: mutable i64 = x\n    value <- assignment_add_one(value)\n    return value\n"
    assignment_source: mutable darray[u8] = []
    for index in 0..<sview_len(assignment_text) |index, assignment_text, assignment_source|:
        assignment_source.push(sview_at(assignment_text, index))
    assignment_source.push(0)
    assignment_file: Ast::File = frontend_parse(&assignment_source[0])
    assignment_report: mutable ProofReport = proof_empty_report()
    proof_check(assignment_file, &assignment_report)
    proof_replay_certificates(&assignment_report)
    assignment_trace_index: mutable usize = assignment_report.traces.records.count
    for index in 0..<assignment_report.traces.records.count |index, assignment_report, assignment_trace_index|:
        candidate: ProofFactTrace = assignment_report.traces.records[index]
        if candidate.kind == "function-summary" and candidate.name == "assignment_rhs_state" and candidate.dependency == "assignment_add_one":
            assignment_trace_index <- index
            break
    return 35 if assignment_trace_index >= assignment_report.traces.records.count
    assignment_report.replay_owner_line <- 6
    return 36 if not proof_replay_fact_trace_entry(&assignment_report, assignment_trace_index)
    reassigned_text: sview = "def assignment_add_one(x: i64) -> i64:\n    requires x >= 0\n    ensure result == x + 1\n    return x + 1\n\ndef assignment_rhs_state(x: i64) -> i64:\n    requires x >= 0\n    ensure result == x + 1\n    value: mutable i64 = x\n    value <- assignment_add_one(value)\n    value <- 0\n    return value\n"
    reassigned_source: mutable darray[u8] = []
    for index in 0..<sview_len(reassigned_text) |index, reassigned_text, reassigned_source|:
        reassigned_source.push(sview_at(reassigned_text, index))
    reassigned_source.push(0)
    reassigned_file: Ast::File = frontend_parse(&reassigned_source[0])
    reassigned_position: mutable Ast::Pos = Ast::pos_at_line(12)
    reassigned_return_found: mutable bool = false
    return 37 if not test_local_return_position_declarations(reassigned_file.top_decls, "assignment_rhs_state", 6, "value", &reassigned_position, &reassigned_return_found, 0)
    return 38 if not reassigned_return_found
    assignment_trace: ProofFactTrace = assignment_report.traces.records[assignment_trace_index]
    assignment_summary: mutable ProofExecutableSummary = ProofExecutableSummary{name: "", line: 0, parameters_start: 0, parameters_count: 0, requires_start: 0, requires_count: 0, ensures_start: 0, ensures_count: 0, pure: false, verified: false, verification_reason: ""}
    assignment_summary_found: mutable bool = false
    for candidate in assignment_report.executables.summaries |candidate, assignment_trace, assignment_summary_found, assignment_summary|:
        if candidate.name == "assignment_add_one" and candidate.line == assignment_trace.owner_line:
            assignment_summary <- candidate
            assignment_summary_found <- true
    return 39 if not assignment_summary_found
    assignment_call: (known: bool, call: Ast::Expr) = test_summary_source_call(&assignment_report, assignment_trace, assignment_summary)
    return 40 if not assignment_call.known
    return 41 if test_summary_local_binding_source(&assignment_report, "assignment_rhs_state", 6, "value", reassigned_position, assignment_call.call)

    trace_index: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, trace_index|:
        if report.traces.records[index].kind == "deterministic-call":
            trace_index <- index
            break
    return 1 if trace_index >= report.traces.records.count
    return 2 if not proof_replay_fact_trace_entry(&report, trace_index)

    original: ProofFactTrace = report.traces.records[trace_index]
    match original.expression:
        Ast::Expr.Call(marker_callee, marker_arguments, marker_names, position):
            return 3 if marker_arguments.count != 1
            match marker_arguments[0]:
                Ast::Expr.Call(call_callee, arguments, argument_names, call_position):
                    forged_position: Ast::Pos = call_position
                    forged_position.line <- forged_position.line + 1
                    forged_position.column <- forged_position.column + 1
                    forged_position.offset <- forged_position.offset + 1
                    forged_position.end_line <- forged_position.end_line + 1
                    forged_position.end_column <- forged_position.end_column + 1
                    forged_position.end_offset <- forged_position.end_offset + 1
                    position_forged_call: Ast::Expr = Ast::Expr.Call(call_callee, arguments, argument_names, forged_position)
                    position_forged_arguments: darray[Ast::Expr] = [position_forged_call]
                    position_forgery: Ast::Expr = Ast::Expr.Call(marker_callee, position_forged_arguments, marker_names, position)
                    position_encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(position_forgery, &report, original.name)
                    return 9 if not position_encoded.known
                    report.traces.records[trace_index] <- ProofFactTrace{expression: position_forgery, kernel_expression: position_encoded.root, kind: original.kind, line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
                    return 10 if proof_replay_fact_trace_entry(&report, trace_index)
                    report.traces.records[trace_index] <- original
                    return 11 if not proof_replay_fact_trace_entry(&report, trace_index)
                    wrong_module: Ast::Expr = Ast::Expr.Scope(Ast::Expr.Ident("Elsewhere", call_position), "Inner", call_position)
                    forged_callee: Ast::Expr = Ast::Expr.Scope(wrong_module, "bounded", call_position)
                    forged_call: Ast::Expr = Ast::Expr.Call(forged_callee, arguments, argument_names, call_position)
                    forged_arguments: darray[Ast::Expr] = [forged_call]
                    forged_expression: Ast::Expr = Ast::Expr.Call(marker_callee, forged_arguments, marker_names, position)
                    encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_expression, &report, original.name)
                    return 4 if not encoded.known
                    report.traces.records[trace_index] <- ProofFactTrace{expression: forged_expression, kernel_expression: encoded.root, kind: original.kind, line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
                    return 5 if proof_replay_fact_trace_entry(&report, trace_index)
                    report.traces.records[trace_index] <- original
                    return 6 if not proof_replay_fact_trace_entry(&report, trace_index)
                _:
                    return 7
        _:
            return 8

    forged_binding_position: Ast::Pos = Ast::pos_at_line(0)
    forged_binding: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("x", forged_binding_position), TokenKind.EqEq, Ast::Expr.IntLit(FORGED_LOCAL_BINDING_VALUE, forged_binding_position), forged_binding_position)
    forged_binding_encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_binding, &report, "caller")
    return FORGED_LOCAL_BINDING_ENCODING_FAILED if not forged_binding_encoded.known
    forged_binding_trace: ProofFactTrace = ProofFactTrace{expression: forged_binding, kernel_expression: forged_binding_encoded.root, kind: "local-binding", line: 0, name: "caller", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
    report.traces.records.push(forged_binding_trace)
    return FORGED_LOCAL_BINDING_ACCEPTED if proof_replay_fact_trace_entry(&report, report.traces.records.count - 1)
    return 0
'''


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="qualified-call-replay-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "qualified_call_replay.elisa"
        executable = directory / "qualified_call_replay"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        harness = HARNESS.replace("../../Elisa-compiler/", compiler_include).replace(
            'include "../src/', 'include "../../src/'
        )
        source.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", "-O2", "-o", str(executable), str(source)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=300,
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 harness compile failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)

    print("qualified call-summary replay: nested value-block calls bind to their source owner; omitted, duplicate and wrong-owner claims fail; existing argument, source-span, reassignment and wrong-module adversarial checks hold")


if __name__ == "__main__":
    main()
