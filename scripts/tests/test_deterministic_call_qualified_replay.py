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
        def test_summary_local_binding_source(report: ProofReport&, owner: sview, local_name: sview, line: u32, call: Ast::Expr) -> bool:
            matches: mutable usize = 0
            return proof_replay_summary_local_call_declarations(report.source_declarations, owner, local_name, line, call, &matches, 0) and matches == 1

using Ast
using ElisaProof

const FORGED_LOCAL_BINDING_VALUE: i64 = 987654321
const FORGED_LOCAL_BINDING_ENCODING_FAILED: i64 = 25
const FORGED_LOCAL_BINDING_ACCEPTED: i64 = 26

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    text: sview = "module Gate:\n    module Inner:\n        public:\n            def bounded(x: i64) -> i64:\n                requires x >= 0\n                ensure result >= 0\n                return x\n\nmodule Elsewhere:\n    module Inner:\n        public:\n            def unrelated(x: i64) -> i64:\n                return x\n\ndef caller(x: i64) -> i64:\n    requires x >= 0\n    ensure result >= 0\n    return Gate::Inner::bounded(x)\n\ndef caller_local(x: i64) -> i64:\n    requires x >= 0\n    ensure result >= 0\n    result_value: i64 = Gate::Inner::bounded(x)\n    return result_value\n"
    source: mutable darray[u8] = []
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    proof_replay_certificates(&report)

    summary_index: mutable usize = report.fact_traces.count
    for index in 0..<report.fact_traces.count |index, report, summary_index|:
        if report.fact_traces[index].kind == "function-summary" and report.fact_traces[index].name == "caller" and report.fact_traces[index].dependency == "bounded":
            summary_index <- index
            break
    return 9 if summary_index >= report.fact_traces.count
    summary_original: ProofFactTrace = report.fact_traces[summary_index]
    return 10 if not proof_replay_fact_trace_entry(&report, summary_index)
    summary_result_index: mutable usize = summary_original.summary_bindings_start
    for offset in 0..<summary_original.summary_bindings_count |offset, summary_original, report, summary_result_index|:
        summary_result_index <- summary_original.summary_bindings_start + offset if report.fact_trace_summary_names[summary_original.summary_bindings_start + offset] == "result"
    return 11 if summary_result_index == summary_original.summary_bindings_start
    summary_result_original: Ast::Expr = report.fact_trace_summary_values[summary_result_index]
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
    report.fact_trace_summary_values[summary_result_index] <- forged_summary_result
    report.fact_traces[summary_index] <- ProofFactTrace{expression: forged_owner_summary, kernel_expression: forged_owner_encoded.root, kind: summary_original.kind, line: summary_original.line, name: summary_original.name, dependency: summary_original.dependency, premises_start: summary_original.premises_start, premises_count: summary_original.premises_count, kernel_premises_start: summary_original.kernel_premises_start, kernel_premises_count: summary_original.kernel_premises_count, summary_bindings_start: summary_original.summary_bindings_start, summary_bindings_count: summary_original.summary_bindings_count, summary_requires_start: summary_original.summary_requires_start, summary_requires_count: summary_original.summary_requires_count, summary_ensure_index: summary_original.summary_ensure_index, owner_line: summary_original.owner_line}
    return 17 if proof_replay_fact_trace_entry(&report, summary_index)
    report.fact_traces[summary_index] <- summary_original
    report.fact_trace_summary_values[summary_result_index] <- summary_result_original
    return 18 if not proof_replay_fact_trace_entry(&report, summary_index)

    report.fact_trace_summary_values[summary_result_index] <- Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression))
    forged_summary: Ast::Expr = Ast::Expr.Binary(Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression)), TokenKind.GtEq, Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression)), Ast::expr_pos(summary_original.expression))
    summary_encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_summary, &report, summary_original.name)
    return 12 if not summary_encoded.known
    report.fact_traces[summary_index] <- ProofFactTrace{expression: forged_summary, kernel_expression: summary_encoded.root, kind: summary_original.kind, line: summary_original.line, name: summary_original.name, dependency: summary_original.dependency, premises_start: summary_original.premises_start, premises_count: summary_original.premises_count, kernel_premises_start: summary_original.kernel_premises_start, kernel_premises_count: summary_original.kernel_premises_count, summary_bindings_start: summary_original.summary_bindings_start, summary_bindings_count: summary_original.summary_bindings_count, summary_requires_start: summary_original.summary_requires_start, summary_requires_count: summary_original.summary_requires_count, summary_ensure_index: summary_original.summary_ensure_index, owner_line: summary_original.owner_line}
    return 13 if proof_replay_fact_trace_entry(&report, summary_index)
    report.fact_traces[summary_index] <- summary_original
    report.fact_trace_summary_values[summary_result_index] <- summary_result_original
    return 14 if not proof_replay_fact_trace_entry(&report, summary_index)

    local_trace_index: mutable usize = report.fact_traces.count
    for index in 0..<report.fact_traces.count |index, report, local_trace_index|:
        candidate: ProofFactTrace = report.fact_traces[index]
        continue if candidate.kind != "function-summary" or candidate.name != "caller_local" or candidate.dependency != "bounded"
        local_trace_index <- index
    return 19 if local_trace_index >= report.fact_traces.count
    local_trace: ProofFactTrace = report.fact_traces[local_trace_index]
    local_result_index: usize = local_trace.summary_bindings_start + 1
    return 20 if local_result_index >= report.fact_trace_summary_values.count
    local_call: mutable Ast::Expr = report.fact_trace_summary_values[local_result_index]
    match local_call:
        Ast::Expr.Paren(inner, _):
            local_call <- inner
        _:
            pass
    local_call_position: Ast::Pos = Ast::expr_pos(local_call)
    return 21 if not test_summary_local_binding_source(&report, "caller_local", "result_value", local_call_position.line, local_call)
    return 22 if test_summary_local_binding_source(&report, "caller_local", "wrong_local", local_call_position.line, local_call)
    summary_argument_index: usize = summary_original.summary_bindings_start
    summary_argument_original: Ast::Expr = report.fact_trace_summary_values[summary_argument_index]
    report.fact_trace_summary_values[summary_argument_index] <- Ast::Expr.IntLit(0, Ast::expr_pos(summary_original.expression))
    return 23 if proof_replay_fact_trace_entry(&report, summary_index)
    report.fact_trace_summary_values[summary_argument_index] <- summary_argument_original
    return 24 if not proof_replay_fact_trace_entry(&report, summary_index)

    trace_index: mutable usize = report.fact_traces.count
    for index in 0..<report.fact_traces.count |index, report, trace_index|:
        if report.fact_traces[index].kind == "deterministic-call":
            trace_index <- index
            break
    return 1 if trace_index >= report.fact_traces.count
    return 2 if not proof_replay_fact_trace_entry(&report, trace_index)

    original: ProofFactTrace = report.fact_traces[trace_index]
    match original.expression:
        Ast::Expr.Call(marker_callee, marker_arguments, marker_names, position):
            return 3 if marker_arguments.count != 1
            match marker_arguments[0]:
                Ast::Expr.Call(call_callee, arguments, argument_names, call_position):
                    forged_position: Ast::Pos = call_position
                    forged_position.offset <- forged_position.offset + 1
                    position_forged_call: Ast::Expr = Ast::Expr.Call(call_callee, arguments, argument_names, forged_position)
                    position_forged_arguments: darray[Ast::Expr] = [position_forged_call]
                    position_forgery: Ast::Expr = Ast::Expr.Call(marker_callee, position_forged_arguments, marker_names, position)
                    position_encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(position_forgery, &report, original.name)
                    return 9 if not position_encoded.known
                    report.fact_traces[trace_index] <- ProofFactTrace{expression: position_forgery, kernel_expression: position_encoded.root, kind: original.kind, line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
                    return 10 if proof_replay_fact_trace_entry(&report, trace_index)
                    report.fact_traces[trace_index] <- original
                    return 11 if not proof_replay_fact_trace_entry(&report, trace_index)
                    wrong_module: Ast::Expr = Ast::Expr.Scope(Ast::Expr.Ident("Elsewhere", call_position), "Inner", call_position)
                    forged_callee: Ast::Expr = Ast::Expr.Scope(wrong_module, "bounded", call_position)
                    forged_call: Ast::Expr = Ast::Expr.Call(forged_callee, arguments, argument_names, call_position)
                    forged_arguments: darray[Ast::Expr] = [forged_call]
                    forged_expression: Ast::Expr = Ast::Expr.Call(marker_callee, forged_arguments, marker_names, position)
                    encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_expression, &report, original.name)
                    return 4 if not encoded.known
                    report.fact_traces[trace_index] <- ProofFactTrace{expression: forged_expression, kernel_expression: encoded.root, kind: original.kind, line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
                    return 5 if proof_replay_fact_trace_entry(&report, trace_index)
                    report.fact_traces[trace_index] <- original
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
    report.fact_traces.push(forged_binding_trace)
    return FORGED_LOCAL_BINDING_ACCEPTED if proof_replay_fact_trace_entry(&report, report.fact_traces.count - 1)
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

    print("qualified call-summary replay: local-result and argument checks hold; wrong local, argument, call-span, same-leaf owner and forged local-binding claims rejected")


if __name__ == "__main__":
    main()
