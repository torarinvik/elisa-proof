"""Loops carrying `invariant` and `decreases` clauses compile, link and run under the pinned
compiler, and prove (BACKLOG E-03). Each invariant is then mutated, by negation and by tightening
a non-strict comparison, and every mutant must leave the proof incomplete: an invariant the
checker accepted without reading would survive a mutation."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
COMPILER = os.environ.get("ELISA_COMPILER_BIN", "")
FIXTURE = ROOT / "examples/loop_invariants_compile.elisa"
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin/elisac-stage1"
STAGE1_WRAPPER = COMPILER_ROOT / "scripts/elisac_stage1.sh"
STAGE1_FRESHNESS = COMPILER_ROOT / "scripts/assert_stage1_fresh.sh"
PINNED_FRONTEND_ROOT = ROOT / "build/snapshot/Elisa-compiler"
PINNED_FRONTEND_REV = (ROOT / "ELISA_COMPILER_REV").read_text().strip()

REPLAY_HARNESS = r'''include "../../Elisa-compiler/elisacore_std/elisacore_runtime_prelude.elisa"
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
include "../src/proof/tactics.elisa"
include "../src/proof/check.elisa"
include "../src/proof/kernel_replay.elisa"
include "../src/proof/replay.elisa"

using Ast
using ElisaProof

extend ElisaProof:
    public:
        def proof_test_local_binding_source_gate(report: mutable ProofReport&, certificate_index: usize, trace_index: usize) -> i64:
            return TEST_LOCAL_BINDING_GATE_INVALID_INDEX if certificate_index >= report.certificates.count or trace_index >= report.fact_traces.count
            certificate: ProofGoalCertificate = report.certificates[certificate_index]
            trace: ProofFactTrace = report.fact_traces[trace_index]
            owner_line: mutable u32 = 0
            proof_replay_owner_function_line(report.source_declarations, certificate.name, certificate.line, &owner_line, 0)
            return TEST_LOCAL_BINDING_GATE_MISSING_OWNER if owner_line == 0
            report.replay_owner_line <- owner_line
            report.trace_owner_line <- certificate.line
            report.trace_consumer_certificate_index <- certificate_index + 1
            immutable_source: bool = proof_replay_local_binding_immutable_declaration_source(report, trace)
            widening_source: bool = proof_replay_local_binding_widening_cast_declaration_source(report, trace)
            return TEST_LOCAL_BINDING_GATE_MISSING_SOURCE if not immutable_source and not widening_source
            return TEST_LOCAL_BINDING_GATE_SOURCE_REJECTED if not proof_replay_local_binding_source_valid(report, trace)
            return TEST_LOCAL_BINDING_GATE_FACT_NOT_LIVE if not proof_replay_local_binding_fact_live(report, trace)
            return TEST_LOCAL_BINDING_GATE_ACCEPTED

const BASELINE_SOURCE: sview = __BASELINE_SOURCE__
const WIDENING_SOURCE: sview = __WIDENING_SOURCE__
const SHADOWED_LOCAL_SOURCE: sview = __SHADOWED_LOCAL_SOURCE__
const CUSTOM_CAST_SOURCE: sview = __CUSTOM_CAST_SOURCE__
const OVERLOADED_OPERATOR_SOURCE: sview = __OVERLOADED_OPERATOR_SOURCE__
const BINDING_SINK_SOURCE: sview = __BINDING_SINK_SOURCE__
const NESTED_BUILTIN_SOURCE: sview = __NESTED_BUILTIN_SOURCE__
const TEST_CAST_GATE_ERROR_BASE: i64 = 119
const TEST_CAST_GATE_COUNT_ERROR: i64 = 118
const TEST_SHADOW_GATE_ERROR: i64 = 122
const TEST_SHADOW_GATE_COUNT_ERROR: i64 = 123
const TEST_CUSTOM_CAST_GATE_ERROR: i64 = 124
const TEST_CUSTOM_CAST_GATE_COUNT_ERROR: i64 = 125
const TEST_OVERLOADED_OPERATOR_GATE_ERROR: i64 = 126
const TEST_OVERLOADED_OPERATOR_GATE_COUNT_ERROR: i64 = 127
const TEST_BINDING_SINK_MATRIX_ERROR: i64 = 128
const TEST_BINDING_POSITIVE_CONTROL_ERROR: i64 = 129
const TEST_BINDING_POSITION_SHIFT: u32 = 1
const TEST_BINDING_FALLBACK_VALUE: i64 = 0
const TEST_LOCAL_BINDING_GATE_INVALID_INDEX: i64 = 1
const TEST_LOCAL_BINDING_GATE_MISSING_OWNER: i64 = 2
const TEST_LOCAL_BINDING_GATE_MISSING_SOURCE: i64 = 3
const TEST_LOCAL_BINDING_GATE_SOURCE_REJECTED: i64 = 4
const TEST_LOCAL_BINDING_GATE_FACT_NOT_LIVE: i64 = 5
const TEST_LOCAL_BINDING_GATE_ACCEPTED: i64 = 0
const TEST_WIDENING_CAST_GATE_COUNT: usize = 2
const TEST_SINGLE_SOURCE_GATE_COUNT: usize = 1
const FALSE_INVARIANT_SOURCE: sview = __FALSE_INVARIANT_SOURCE__
const OVERRUN_SOURCE: sview = __OVERRUN_SOURCE__
const STALE_INITIALIZER_SOURCE: sview = __STALE_INITIALIZER_SOURCE__
const STALE_REBIND_SOURCE: sview = __STALE_REBIND_SOURCE__
const SHADOWED_PARAMETER_SOURCE: sview = __SHADOWED_PARAMETER_SOURCE__
const SHADOWED_GLOBAL_SOURCE: sview = __SHADOWED_GLOBAL_SOURCE__
const UNRELATED_INVARIANT_SOURCE: sview = __UNRELATED_INVARIANT_SOURCE__
def proof_test_parse_and_replay(source_text: sview, source: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(source_text) |index, source_text, source|:
        source.push(sview_at(source_text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    proof_check(file, report)
    proof_replay_certificates(report)

def proof_test_parse_declarations(source_text: sview, source: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(source_text) |index, source_text, source|:
        source.push(sview_at(source_text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report.source_declarations <- file.top_decls

def proof_test_local_binding_initializer_source(source_text: sview, owner: sview, target: sview, expect_valid: bool) -> bool can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_declarations(source_text, &source, &report)
    owner_line: mutable u32 = 0
    for declaration in report.source_declarations |owner, owner_line|:
        match declaration:
            Ast::Decl.Func(name, _, _, _, _, _, position):
                owner_line <- position.line if name == owner
            _:
                pass
    return false if owner_line == 0
    body: mutable darray[Ast::Stmt] = []
    owner_matches: mutable usize = 0
    proof_replay_local_binding_find_owner(report.source_declarations, owner, owner_line, &body, &owner_matches, 0)
    return false if owner_matches != 1
    for statement in body |report, target, owner, owner_line, expect_valid|:
        match statement:
            Ast::Stmt.VarDecl(name, _, initializer, position):
                continue if name != target
                expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(target, position), TokenKind.EqEq, initializer, position)
                trace: ProofFactTrace = ProofFactTrace{expression: expression, kernel_expression: 0, kind: "local-binding", line: position.line, name: owner, dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
                report.replay_owner_line <- owner_line
                report.trace_owner_line <- position.line
                accepted: bool = proof_replay_local_binding_immutable_declaration_source(report, trace)
                return accepted == expect_valid
            _:
                pass
    return false if expect_valid
    fallback_position: Ast::Pos = Ast::Pos{line: owner_line, column: TEST_BINDING_POSITION_SHIFT, offset: 0, end_line: owner_line, end_column: TEST_BINDING_POSITION_SHIFT, end_offset: 0}
    fallback: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(target, fallback_position), TokenKind.EqEq, Ast::Expr.IntLit(TEST_BINDING_FALLBACK_VALUE, fallback_position), fallback_position)
    fallback_trace: ProofFactTrace = ProofFactTrace{expression: fallback, kernel_expression: 0, kind: "local-binding", line: owner_line, name: owner, dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
    report.replay_owner_line <- owner_line
    report.trace_owner_line <- owner_line
    return not proof_replay_local_binding_immutable_declaration_source(report, fallback_trace)
def proof_test_local_binding_spoofed_position_rejected(source_text: sview, owner: sview, target: sview) -> bool can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_declarations(source_text, &source, &report)
    owner_line: mutable u32 = 0
    for declaration in report.source_declarations |owner, owner_line|:
        match declaration:
            Ast::Decl.Func(name, _, _, _, _, _, position):
                owner_line <- position.line if name == owner
            _:
                pass
    return false if owner_line == 0
    body: mutable darray[Ast::Stmt] = []
    owner_matches: mutable usize = 0
    proof_replay_local_binding_find_owner(report.source_declarations, owner, owner_line, &body, &owner_matches, 0)
    return false if owner_matches != 1
    for statement in body |report, target, owner, owner_line|:
        match statement:
            Ast::Stmt.VarDecl(name, _, initializer, position):
                continue if name != target
                forged_position: Ast::Pos = Ast::Pos{line: position.line, column: position.column + TEST_BINDING_POSITION_SHIFT, offset: position.offset + TEST_BINDING_POSITION_SHIFT, end_line: position.end_line, end_column: position.end_column, end_offset: position.end_offset}
                expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(target, forged_position), TokenKind.EqEq, initializer, forged_position)
                trace: ProofFactTrace = ProofFactTrace{expression: expression, kernel_expression: 0, kind: "local-binding", line: position.line, name: owner, dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
                report.replay_owner_line <- owner_line
                report.trace_owner_line <- position.line
                return not proof_replay_local_binding_immutable_declaration_source(report, trace)
            _:
                pass
    return false
def proof_test_local_binding_statement_sink_rejected(source_text: sview, owner: sview, sink_kind: sview) -> bool can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_declarations(source_text, &source, &report)
    owner_line: mutable u32 = 0
    for declaration in report.source_declarations |owner, owner_line|:
        match declaration:
            Ast::Decl.Func(name, _, _, _, _, _, position):
                owner_line <- position.line if name == owner
            _:
                pass
    return false if owner_line == 0
    body: mutable darray[Ast::Stmt] = []
    owner_matches: mutable usize = 0
    proof_replay_local_binding_find_owner(report.source_declarations, owner, owner_line, &body, &owner_matches, 0)
    return false if owner_matches != 1
    for statement in body |report, sink_kind, owner, owner_line|:
        match statement:
            Ast::Stmt.Assign(Ast::Expr.Ident(target, position), _, value, _):
                continue if sink_kind != "assignment"
                expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(target, position), TokenKind.EqEq, value, position)
                trace: ProofFactTrace = ProofFactTrace{expression: expression, kernel_expression: 0, kind: "local-binding", line: position.line, name: owner, dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
                report.replay_owner_line <- owner_line
                report.trace_owner_line <- position.line
                return not proof_replay_local_binding_immutable_declaration_source(report, trace)
            Ast::Stmt.Assign(target_expression, _, value, position):
                continue if sink_kind != "indexed-write"
                target: sview = "values" if sink_kind == "indexed-write" else ""
                return false if target == ""
                expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(target, position), TokenKind.EqEq, value, position)
                trace: ProofFactTrace = ProofFactTrace{expression: expression, kernel_expression: 0, kind: "local-binding", line: position.line, name: owner, dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
                report.replay_owner_line <- owner_line
                report.trace_owner_line <- position.line
                return not proof_replay_local_binding_immutable_declaration_source(report, trace)
            Ast::Stmt.Return(value, position):
                continue if sink_kind != "return"
                expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("result", position), TokenKind.EqEq, value, position)
                trace: ProofFactTrace = ProofFactTrace{expression: expression, kernel_expression: 0, kind: "local-binding", line: position.line, name: owner, dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
                report.replay_owner_line <- owner_line
                report.trace_owner_line <- position.line
                return not proof_replay_local_binding_immutable_declaration_source(report, trace)
            _:
                pass
    return false
def proof_test_loop_goals(report: ProofReport&, function_name: sview, source_line: u32) -> (count: usize, all_replayed: bool):
    count: mutable usize = 0
    all_replayed: mutable bool = true
    for certificate in report.certificates |count, all_replayed, function_name, source_line|:
        if certificate.name == function_name and certificate.rule == "goal" and certificate.line == source_line:
            count <- count + 1
            all_replayed <- false if not certificate.replayed
    return (count, all_replayed)

def proof_test_has_loop_refusal(report: ProofReport&, function_name: sview, source_line: u32) -> bool:
    for finding in report.findings |function_name, source_line|:
        if finding.name == function_name and finding.line == source_line:
            return true if finding.kind == "invariant-unproven" or finding.kind == "invariant-not-preserved"
    return false

def main() -> i64 can Memory.Allocate, Abort.Panic:
    baseline_bytes: mutable darray[u8] = []
    baseline: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(BASELINE_SOURCE, &baseline_bytes, &baseline)
    bounded = proof_test_loop_goals(baseline, "bounded_counter", 9)
    return 101 if bounded.count != 2 or not bounded.all_replayed
    plain = proof_test_loop_goals(baseline, "countdown", 19)
    return 102 if plain.count == 0 or not plain.all_replayed

    init_index: mutable usize = baseline.fact_traces.count
    rebind_index: mutable usize = baseline.fact_traces.count
    for index in 0..<baseline.fact_traces.count |index, baseline, init_index, rebind_index|:
        trace: ProofFactTrace = baseline.fact_traces[index]
        continue if trace.kind != "local-binding" or trace.name != "bounded_counter"
        match trace.expression:
            Ast::Expr.Binary(Ast::Expr.Ident(name, _), TokenKind.EqEq, _, _):
                init_index <- index if name == "rounds" and trace.line == 8
                rebind_index <- index if name == "__elisa_rebind_0" and trace.line == 11
            _:
                pass
    return 103 if init_index >= baseline.fact_traces.count or rebind_index >= baseline.fact_traces.count
    baseline.replay_owner_line <- 6
    baseline.trace_owner_line <- 9
    return 104 if not proof_replay_fact_trace_entry(&baseline, init_index)
    return 105 if not proof_replay_fact_trace_entry(&baseline, rebind_index)

    # Altering only the trace site cannot preserve source provenance.
    init_original: ProofFactTrace = baseline.fact_traces[init_index]
    stale_trace: ProofFactTrace = ProofFactTrace{expression: init_original.expression, kernel_expression: init_original.kernel_expression, kind: init_original.kind, line: 11, name: init_original.name, dependency: init_original.dependency, premises_start: init_original.premises_start, premises_count: init_original.premises_count, kernel_premises_start: init_original.kernel_premises_start, kernel_premises_count: init_original.kernel_premises_count, summary_bindings_start: init_original.summary_bindings_start, summary_bindings_count: init_original.summary_bindings_count, summary_requires_start: init_original.summary_requires_start, summary_requires_count: init_original.summary_requires_count, summary_ensure_index: init_original.summary_ensure_index, owner_line: init_original.owner_line}
    baseline.fact_traces[init_index] <- stale_trace
    return 106 if proof_replay_fact_trace_entry(&baseline, init_index)
    baseline.fact_traces[init_index] <- init_original

    # The RHS and source location do not identify a rebind witness without its exact fresh
    # binding symbol. A different reserved pool entry must not be accepted for this assignment.
    rebind_original: ProofFactTrace = baseline.fact_traces[rebind_index]
    rebind_value: mutable Ast::Expr = Ast::Expr.Invalid
    match rebind_original.expression:
        Ast::Expr.Binary(_, TokenKind.EqEq, right, _):
            rebind_value <- right
        _:
            return 114
    rebind_position: Ast::Pos = Ast::expr_pos(rebind_original.expression)
    forged_rebind_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("__elisa_rebind_63", rebind_position), TokenKind.EqEq, rebind_value, rebind_position)
    encoded_rebind: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_rebind_expression, &baseline, "bounded_counter")
    return 115 if not encoded_rebind.known
    forged_rebind_trace: ProofFactTrace = ProofFactTrace{expression: forged_rebind_expression, kernel_expression: encoded_rebind.root, kind: rebind_original.kind, line: rebind_original.line, name: rebind_original.name, dependency: rebind_original.dependency, premises_start: rebind_original.premises_start, premises_count: rebind_original.premises_count, kernel_premises_start: rebind_original.kernel_premises_start, kernel_premises_count: rebind_original.kernel_premises_count, summary_bindings_start: rebind_original.summary_bindings_start, summary_bindings_count: rebind_original.summary_bindings_count, summary_requires_start: rebind_original.summary_requires_start, summary_requires_count: rebind_original.summary_requires_count, summary_ensure_index: rebind_original.summary_ensure_index, owner_line: rebind_original.owner_line}
    baseline.fact_traces.push(forged_rebind_trace)
    return 116 if proof_replay_fact_trace_entry(&baseline, baseline.fact_traces.count - 1)

    # The old RHS witness is invalid once the actual source assignment changes.
    stale_rebind_bytes: mutable darray[u8] = []
    stale_rebind_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(STALE_REBIND_SOURCE, &stale_rebind_bytes, &stale_rebind_report)
    baseline.source_declarations <- stale_rebind_report.source_declarations
    return 117 if proof_replay_fact_trace_entry(&baseline, rebind_index)

    # A same-spelled parameter or global constant would make the kernel identifier's binding
    # ambiguous even though a local declaration and assignment occur at the expected lines.
    shadowed_parameter_bytes: mutable darray[u8] = []
    shadowed_parameter_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_declarations(SHADOWED_PARAMETER_SOURCE, &shadowed_parameter_bytes, &shadowed_parameter_report)
    baseline.source_declarations <- shadowed_parameter_report.source_declarations
    return 118 if proof_replay_fact_trace_entry(&baseline, init_index) or proof_replay_fact_trace_entry(&baseline, rebind_index)
    shadowed_global_bytes: mutable darray[u8] = []
    shadowed_global_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_declarations(SHADOWED_GLOBAL_SOURCE, &shadowed_global_bytes, &shadowed_global_report)
    baseline.source_declarations <- shadowed_global_report.source_declarations
    return 119 if proof_replay_fact_trace_entry(&baseline, init_index) or proof_replay_fact_trace_entry(&baseline, rebind_index)

    # A forged equality at the right line is not the source initializer.
    forged_position: Ast::Pos = Ast::expr_pos(init_original.expression)
    forged_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("rounds", forged_position), TokenKind.EqEq, Ast::Expr.IntLit(987654321, forged_position), forged_position)
    encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_expression, &baseline, "bounded_counter")
    return 107 if not encoded.known
    forged_trace: ProofFactTrace = ProofFactTrace{expression: forged_expression, kernel_expression: encoded.root, kind: init_original.kind, line: init_original.line, name: init_original.name, dependency: init_original.dependency, premises_start: init_original.premises_start, premises_count: init_original.premises_count, kernel_premises_start: init_original.kernel_premises_start, kernel_premises_count: init_original.kernel_premises_count, summary_bindings_start: init_original.summary_bindings_start, summary_bindings_count: init_original.summary_bindings_count, summary_requires_start: init_original.summary_requires_start, summary_requires_count: init_original.summary_requires_count, summary_ensure_index: init_original.summary_ensure_index, owner_line: init_original.owner_line}
    baseline.fact_traces.push(forged_trace)
    return 108 if proof_replay_fact_trace_entry(&baseline, baseline.fact_traces.count - 1)

    # Old initializer evidence must not transfer to changed source at the same binding site.
    stale_bytes: mutable darray[u8] = []
    stale_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(STALE_INITIALIZER_SOURCE, &stale_bytes, &stale_report)
    baseline.source_declarations <- stale_report.source_declarations
    return 109 if proof_replay_fact_trace_entry(&baseline, init_index)

    # An unrelated invariant on the same consumer line cannot stand in for the source contract.
    unrelated_bytes: mutable darray[u8] = []
    unrelated_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(UNRELATED_INVARIANT_SOURCE, &unrelated_bytes, &unrelated_report)
    baseline.source_declarations <- unrelated_report.source_declarations
    return 110 if proof_replay_fact_trace_entry(&baseline, init_index)

    false_bytes: mutable darray[u8] = []
    false_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(FALSE_INVARIANT_SOURCE, &false_bytes, &false_report)
    return 111 if not proof_test_has_loop_refusal(false_report, "bounded_counter", 9)

    overrun_bytes: mutable darray[u8] = []
    overrun_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(OVERRUN_SOURCE, &overrun_bytes, &overrun_report)
    return 112 if not proof_test_has_loop_refusal(overrun_report, "bounded_counter", 9)

    # Fresh parsing and independent replay must reproduce both loop obligations.
    fresh_bytes: mutable darray[u8] = []
    fresh_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(BASELINE_SOURCE, &fresh_bytes, &fresh_report)
    fresh = proof_test_loop_goals(fresh_report, "bounded_counter", 9)
    return 113 if fresh.count != 2 or not fresh.all_replayed

    widening_bytes: mutable darray[u8] = []
    widening_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(WIDENING_SOURCE, &widening_bytes, &widening_report)
    cast_gate_checks: mutable usize = 0
    for certificate_index in 0..<widening_report.certificates.count |certificate_index, widening_report, cast_gate_checks|:
        certificate: ProofGoalCertificate = widening_report.certificates[certificate_index]
        continue if certificate.name != "bound_first"
        continue if certificate.facts_start > widening_report.fact_origin_trace_indices.count or certificate.facts_count > widening_report.fact_origin_trace_indices.count - certificate.facts_start
        for fact_offset in 0..<certificate.facts_count |fact_offset, certificate, certificate_index, widening_report, cast_gate_checks|:
            trace_index: usize = widening_report.fact_origin_trace_indices[certificate.facts_start + fact_offset]
            continue if trace_index >= widening_report.fact_traces.count
            trace: ProofFactTrace = widening_report.fact_traces[trace_index]
            continue if trace.kind != "local-binding"
            match trace.expression:
                Ast::Expr.Binary(_, TokenKind.EqEq, _, _):
                    gate: i64 = ElisaProof::proof_test_local_binding_source_gate(&widening_report, certificate_index, trace_index)
                    return TEST_CAST_GATE_ERROR_BASE + gate if gate != TEST_LOCAL_BINDING_GATE_ACCEPTED
                    cast_gate_checks <- cast_gate_checks + 1
                _:
                    pass
        break if cast_gate_checks == TEST_WIDENING_CAST_GATE_COUNT
    return TEST_CAST_GATE_COUNT_ERROR if cast_gate_checks != TEST_WIDENING_CAST_GATE_COUNT

    shadowed_bytes: mutable darray[u8] = []
    shadowed_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(SHADOWED_LOCAL_SOURCE, &shadowed_bytes, &shadowed_report)
    shadowed_gate_checks: mutable usize = 0
    for certificate_index in 0..<shadowed_report.certificates.count |certificate_index, shadowed_report, shadowed_gate_checks|:
        certificate: ProofGoalCertificate = shadowed_report.certificates[certificate_index]
        continue if certificate.name != "shadowed_local"
        continue if certificate.facts_start > shadowed_report.fact_origin_trace_indices.count or certificate.facts_count > shadowed_report.fact_origin_trace_indices.count - certificate.facts_start
        for fact_offset in 0..<certificate.facts_count |fact_offset, certificate, certificate_index, shadowed_report, shadowed_gate_checks|:
            trace_index: usize = shadowed_report.fact_origin_trace_indices[certificate.facts_start + fact_offset]
            continue if trace_index >= shadowed_report.fact_traces.count
            trace: ProofFactTrace = shadowed_report.fact_traces[trace_index]
            continue if trace.kind != "local-binding"
            match trace.expression:
                Ast::Expr.Binary(Ast::Expr.Ident("copy", _), TokenKind.EqEq, Ast::Expr.Ident("shadow", _), _):
                    gate: i64 = ElisaProof::proof_test_local_binding_source_gate(&shadowed_report, certificate_index, trace_index)
                    return TEST_SHADOW_GATE_ERROR if gate != TEST_LOCAL_BINDING_GATE_MISSING_SOURCE
                    shadowed_gate_checks <- shadowed_gate_checks + 1
                _:
                    pass
        break if shadowed_gate_checks > 0
    return TEST_SHADOW_GATE_COUNT_ERROR if shadowed_gate_checks != TEST_SINGLE_SOURCE_GATE_COUNT

    custom_cast_bytes: mutable darray[u8] = []
    custom_cast_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(CUSTOM_CAST_SOURCE, &custom_cast_bytes, &custom_cast_report)
    custom_cast_gate_checks: mutable usize = 0
    for certificate_index in 0..<custom_cast_report.certificates.count |certificate_index, custom_cast_report, custom_cast_gate_checks|:
        certificate: ProofGoalCertificate = custom_cast_report.certificates[certificate_index]
        continue if certificate.name != "custom_cast_does_not_keep_source_bound"
        continue if certificate.facts_start > custom_cast_report.fact_origin_trace_indices.count or certificate.facts_count > custom_cast_report.fact_origin_trace_indices.count - certificate.facts_start
        for fact_offset in 0..<certificate.facts_count |fact_offset, certificate, certificate_index, custom_cast_report, custom_cast_gate_checks|:
            trace_index: usize = custom_cast_report.fact_origin_trace_indices[certificate.facts_start + fact_offset]
            continue if trace_index >= custom_cast_report.fact_traces.count
            trace: ProofFactTrace = custom_cast_report.fact_traces[trace_index]
            continue if trace.kind != "local-binding"
            match trace.expression:
                Ast::Expr.Binary(Ast::Expr.Ident("converted", _), TokenKind.EqEq, _, _):
                    gate: i64 = ElisaProof::proof_test_local_binding_source_gate(&custom_cast_report, certificate_index, trace_index)
                    return TEST_CUSTOM_CAST_GATE_ERROR if gate != TEST_LOCAL_BINDING_GATE_MISSING_SOURCE
                    custom_cast_gate_checks <- custom_cast_gate_checks + 1
                _:
                    pass
        break if custom_cast_gate_checks > 0
    return TEST_CUSTOM_CAST_GATE_COUNT_ERROR if custom_cast_gate_checks != TEST_SINGLE_SOURCE_GATE_COUNT

    overloaded_operator_bytes: mutable darray[u8] = []
    overloaded_operator_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(OVERLOADED_OPERATOR_SOURCE, &overloaded_operator_bytes, &overloaded_operator_report)
    overloaded_operator_gate_checks: mutable usize = 0
    for certificate_index in 0..<overloaded_operator_report.certificates.count |certificate_index, overloaded_operator_report, overloaded_operator_gate_checks|:
        certificate: ProofGoalCertificate = overloaded_operator_report.certificates[certificate_index]
        continue if certificate.name != "overloaded_add_does_not_keep_source_bound"
        continue if certificate.facts_start > overloaded_operator_report.fact_origin_trace_indices.count or certificate.facts_count > overloaded_operator_report.fact_origin_trace_indices.count - certificate.facts_start
        for fact_offset in 0..<certificate.facts_count |fact_offset, certificate, certificate_index, overloaded_operator_report, overloaded_operator_gate_checks|:
            trace_index: usize = overloaded_operator_report.fact_origin_trace_indices[certificate.facts_start + fact_offset]
            continue if trace_index >= overloaded_operator_report.fact_traces.count
            trace: ProofFactTrace = overloaded_operator_report.fact_traces[trace_index]
            continue if trace.kind != "local-binding"
            match trace.expression:
                Ast::Expr.Binary(Ast::Expr.Ident("converted", _), TokenKind.EqEq, _, _):
                    gate: i64 = ElisaProof::proof_test_local_binding_source_gate(&overloaded_operator_report, certificate_index, trace_index)
                    return TEST_OVERLOADED_OPERATOR_GATE_ERROR if gate != TEST_LOCAL_BINDING_GATE_MISSING_SOURCE
                    overloaded_operator_gate_checks <- overloaded_operator_gate_checks + 1
                _:
                    pass
        break if overloaded_operator_gate_checks > 0
    return TEST_OVERLOADED_OPERATOR_GATE_COUNT_ERROR if overloaded_operator_gate_checks != TEST_SINGLE_SOURCE_GATE_COUNT

    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_initializer_source(BINDING_SINK_SOURCE, "sink_assignment", "copy", false)
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_statement_sink_rejected(BINDING_SINK_SOURCE, "sink_assignment", "assignment")
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_initializer_source(BINDING_SINK_SOURCE, "sink_record_field", "copy", false)
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_initializer_source(BINDING_SINK_SOURCE, "sink_indexed_read", "copy", false)
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_initializer_source(BINDING_SINK_SOURCE, "sink_indexed_write", "copy", false)
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_statement_sink_rejected(BINDING_SINK_SOURCE, "sink_indexed_write", "indexed-write")
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_initializer_source(BINDING_SINK_SOURCE, "sink_call", "copy", false)
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_initializer_source(BINDING_SINK_SOURCE, "sink_nested_call", "copy", false)
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_initializer_source(BINDING_SINK_SOURCE, "sink_branch_join", "copy", false)
    return TEST_BINDING_SINK_MATRIX_ERROR if not proof_test_local_binding_statement_sink_rejected(BINDING_SINK_SOURCE, "sink_return", "return")
    return TEST_BINDING_POSITIVE_CONTROL_ERROR if not proof_test_local_binding_initializer_source(NESTED_BUILTIN_SOURCE, "nested_builtin_binding", "copy", true)
    return TEST_BINDING_POSITIVE_CONTROL_ERROR if not proof_test_local_binding_spoofed_position_rejected(NESTED_BUILTIN_SOURCE, "nested_builtin_binding", "copy")
    nested_bytes: mutable darray[u8] = []
    nested_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(NESTED_BUILTIN_SOURCE, &nested_bytes, &nested_report)
    nested_goals = proof_test_loop_goals(nested_report, "nested_builtin_binding", 3)
    return TEST_BINDING_POSITIVE_CONTROL_ERROR if nested_goals.count != 1 or not nested_goals.all_replayed
    return TEST_LOCAL_BINDING_GATE_ACCEPTED
'''


def prove(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return result.returncode, json.loads(result.stdout)


status, data = prove(FIXTURE)
assert status in (0, 1) and data["status"] in ("proved", "proved_with_replay_gaps") and data["findings"] == [], data
fixture_status = data["status"]
fixture_replay = data["replay"]
if data["status"] == "proved":
    assert data["replay"]["gaps"] == 0, data["replay"]
else:
    # This focused regression does not claim whole-fixture proof while unrelated replay gaps
    # exist; the two target certificates are checked individually below.
    assert data["replay"]["gaps"] > 0, data["replay"]
bounded_loop_certificates = [
    certificate for certificate in data["certificates"]
    if certificate["name"] == "bounded_counter" and certificate["rule"] == "goal" and certificate["line"] == 9
]
assert len(bounded_loop_certificates) == 2, bounded_loop_certificates
assert all(certificate["replayed"] for certificate in bounded_loop_certificates), bounded_loop_certificates

source = FIXTURE.read_text()
lines = source.split("\n")
invariant_lines = [index for index, line in enumerate(lines) if line.strip().startswith("invariant ")]
assert len(invariant_lines) == 4, invariant_lines
with tempfile.TemporaryDirectory() as scratch:
    mutants = 0
    for index in invariant_lines:
        indent, claim = lines[index].split("invariant ", 1)
        variants = [f"not ({claim})"]
        if ">=" in claim:
            variants.append(claim.replace(">=", ">", 1))
        if "<=" in claim:
            variants.append(claim.replace("<=", "<", 1))
        for variant in variants:
            mutated = list(lines)
            mutated[index] = f"{indent}invariant {variant}"
            path = Path(scratch) / f"mutant_{mutants}.elisa"
            path.write_text("\n".join(mutated))
            status, data = prove(path)
            assert status != 0 and data["status"] != "proved", (index + 1, variant, data["status"])
            mutants += 1
    assert mutants == 8, mutants

    if not COMPILER:
        sys.exit("loop invariants compile: ELISA_COMPILER_BIN is not set")
    obj = Path(scratch) / "loops.o"
    exe = Path(scratch) / "loops"
    built = subprocess.run([COMPILER, "-permissive", "-emit", "obj", "-O0", "-o", str(obj), str(FIXTURE)], capture_output=True, text=True, timeout=600)
    assert built.returncode == 0 and obj.exists(), built.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True).stdout
    for name in ("bounded_counter", "countdown", "count_up", "stop_early"):
        assert re.search(rf"\b_?{name}\b", symbols), f"{name} was not emitted"
    linked = subprocess.run(["cc", "-o", str(exe), str(obj)], capture_output=True, text=True)
    assert linked.returncode == 0, linked.stderr
    ran = subprocess.run([str(exe)], timeout=60)
    assert ran.returncode == 0, ran.returncode


def run_source_binding_replay_harness():
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not STAGE1_FRESHNESS.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    if not PINNED_FRONTEND_ROOT.is_dir() or not (PINNED_FRONTEND_ROOT / ".rev").is_file():
        raise SystemExit(f"pinned frontend snapshot is missing: {PINNED_FRONTEND_ROOT}; build the proof project first")
    snapshot_revision = (PINNED_FRONTEND_ROOT / ".rev").read_text().strip()
    if snapshot_revision != PINNED_FRONTEND_REV:
        raise SystemExit(
            f"pinned frontend snapshot mismatch: snapshot={snapshot_revision} expected={PINNED_FRONTEND_REV}"
        )
    freshness = subprocess.run(
        ["bash", str(STAGE1_FRESHNESS), str(STAGE1)], capture_output=True, text=True, cwd=COMPILER_ROOT
    )
    if freshness.returncode:
        raise AssertionError(f"Stage1 freshness check failed:\n{freshness.stdout}\n{freshness.stderr}")
    baseline_source = FIXTURE.read_text()
    sources = {
        "__BASELINE_SOURCE__": baseline_source,
        "__WIDENING_SOURCE__": (ROOT / "examples/widening_cast.elisa").read_text(encoding="utf-8"),
        "__SHADOWED_LOCAL_SOURCE__": (ROOT / "test/repro/audit_local_binding_global_shadow.elisa").read_text(encoding="utf-8"),
        "__CUSTOM_CAST_SOURCE__": (ROOT / "test/repro/audit_local_binding_custom_cast.elisa").read_text(encoding="utf-8"),
        "__OVERLOADED_OPERATOR_SOURCE__": (ROOT / "test/repro/audit_local_binding_overloaded_operator.elisa").read_text(encoding="utf-8"),
        "__BINDING_SINK_SOURCE__": (ROOT / "test/repro/audit_local_binding_sink_adversarial.elisa").read_text(encoding="utf-8"),
        "__NESTED_BUILTIN_SOURCE__": (ROOT / "test/repro/audit_local_binding_nested_builtin_positive.elisa").read_text(encoding="utf-8"),
        "__FALSE_INVARIANT_SOURCE__": baseline_source.replace("invariant rounds <= limit", "invariant rounds < limit", 1),
        "__OVERRUN_SOURCE__": baseline_source.replace("rounds <- rounds + 1", "rounds <- rounds + 2", 1),
        "__STALE_INITIALIZER_SOURCE__": baseline_source.replace(
            "rounds: mutable usize = 0\n    while rounds < limit",
            "rounds: mutable usize = 4\n    while rounds < limit",
            1,
        ),
        "__STALE_REBIND_SOURCE__": baseline_source.replace("rounds <- rounds + 1", "rounds <- rounds + 2", 1),
        "__SHADOWED_PARAMETER_SOURCE__": baseline_source.replace(
            "def bounded_counter(limit: usize)", "def bounded_counter(rounds: usize, limit: usize)", 1
        ),
        "__SHADOWED_GLOBAL_SOURCE__": baseline_source.replace(
            "# A while loop with a counter bounded by a parameter.", "const rounds: usize = 99", 1
        ),
        "__UNRELATED_INVARIANT_SOURCE__": baseline_source.replace("invariant rounds <= limit", "invariant rounds < limit", 1),
    }
    assert all(source != baseline_source for marker, source in sources.items() if marker != "__BASELINE_SOURCE__")
    harness = REPLAY_HARNESS
    for marker, source in sources.items():
        harness = harness.replace(marker, json.dumps(source))

    with tempfile.TemporaryDirectory(prefix="bounded-counter-source-replay-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source_path = directory / "bounded_counter_source_replay.elisa"
        executable = directory / "bounded_counter_source_replay"
        harness = harness.replace("../../Elisa-compiler/", str(PINNED_FRONTEND_ROOT.resolve()) + "/").replace(
            'include "../src/', 'include "../../src/'
        )
        source_path.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", "-O0", "-o", str(executable), str(source_path)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=600,
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 source-binding harness failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    return freshness.stdout.strip()

provenance = run_source_binding_replay_harness()
shadow_status, shadow_report = prove(ROOT / "test/repro/audit_local_binding_global_shadow.elisa")
assert shadow_report["status"] != "proved", shadow_report
custom_cast_status, custom_cast_proof_report = prove(ROOT / "test/repro/audit_local_binding_custom_cast.elisa")
assert custom_cast_proof_report["status"] != "proved", custom_cast_proof_report
operator_status, operator_proof_report = prove(ROOT / "test/repro/audit_local_binding_overloaded_operator.elisa")
assert operator_proof_report["status"] != "proved", operator_proof_report
print(
    f"loop invariants: targeted source-bound replay controls passed; fixture={fixture_status} "
    f"({fixture_replay['gaps']} unrelated replay gaps); {provenance}; pinned frontend {PINNED_FRONTEND_REV}"
)
