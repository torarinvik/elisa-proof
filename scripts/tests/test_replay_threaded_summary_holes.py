"""Adversarial replay probes for threaded `&` call summaries (value_threading.elisa).

A call `bump(&x)` through an exclusive `mutable T&` parameter is recorded as a function summary
with an extra `__threaded_state = S` binding: S names x's value after the call. The probe parses a
small source, runs the checker, then forges the threaded summary the way a buggy or hostile
producer could and calls the replay validator directly. Forgeries must be refused; the honest
summary beside them must still be accepted:

- S must be a rebind symbol that no local binding defines;
- the callee must declare no Unsafe effect and no region parameter, and every reference
  parameter must be mutable and threaded;
- each threaded argument must lend a non-reference local of the owner, and no local may be lent
  to two threaded parameters;
- only a validated threaded call keeps a local's own symbol alive across the call.
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

# Line numbers below are fixed by SOURCE_TEXT; keep them in step with it.
SOURCE_TEXT = (
    "def bump(value: mutable u64&) -> void:\n"  # 1
    "    requires value[0] < 1000\n"  # 2
    "    ensure value[0] == old(value[0]) + 1\n"  # 3
    "    value[0] <- value[0] + 1\n"  # 4
    "    return\n"  # 5
    "\n"  # 6
    "def lent() -> u64:\n"  # 7
    "    x: mutable u64 = 5\n"  # 8
    "    bump(&x)\n"  # 9
    "    return x\n"  # 10
    "\n"  # 11
    "def bump_unsafe(value: mutable u64&) -> void can[Unsafe.Alias]:\n"  # 12
    "    requires value[0] < 1000\n"  # 13
    "    ensure value[0] == old(value[0]) + 1\n"  # 14
    "    value[0] <- value[0] + 1\n"  # 15
    "    return\n"  # 16
    "\n"  # 17
    "def keep[@r](value: mutable u64& @r) -> void:\n"  # 18
    "    value[0] <- 1\n"  # 19
    "    return\n"  # 20
    "\n"  # 21
    "def peek(value: u64&) -> u64:\n"  # 22
    "    return value[0]\n"  # 23
    "\n"  # 24
    "def via_ref() -> u64:\n"  # 25
    "    x: mutable u64 = 5\n"  # 26
    "    r: mutable u64& = &x\n"  # 27
    "    bump(r)\n"  # 28
    "    return x\n"  # 29
    "\n"  # 30
    "def bump_both(first: mutable u64&, second: mutable u64&) -> void:\n"  # 31
    "    requires first[0] < 1000\n"  # 32
    "    requires second[0] < 1000\n"  # 33
    "    ensure first[0] == old(first[0]) + 1\n"  # 34
    "    ensure second[0] == old(second[0]) + 1\n"  # 35
    "    first[0] <- first[0] + 1\n"  # 36
    "    second[0] <- second[0] + 1\n"  # 37
    "    return\n"  # 38
)

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
        def test_threaded_retrace(trace: ProofFactTrace, name: sview, line: u32, bindings_start: usize, bindings_count: usize) -> ProofFactTrace:
            return ProofFactTrace{expression: trace.expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: line, name: name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: bindings_start, summary_bindings_count: bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}

        # The function summary of `owner` at `line` that carries a threaded binding.
        def test_threaded_summary(report: ProofReport&, owner: sview, line: u32) -> usize:
            for index in 0..<report.traces.records.count |index, report, owner, line|:
                trace: ProofFactTrace = report.traces.records[index]
                continue if trace.kind != "function-summary" or trace.name != owner or trace.line != line
                for offset in 0..<trace.summary_bindings_count |offset, trace, report, index|:
                    return index if report.traces.summary_names[trace.summary_bindings_start + offset] == "__threaded_state"
            return report.traces.records.count

        def test_threaded_executable(report: ProofReport&, name: sview) -> (known: bool, summary: ProofExecutableSummary):
            for candidate in report.executables.summaries |candidate, name|:
                return (true, candidate) if candidate.name == name
            return (false, ProofExecutableSummary{name: "", line: 0, parameters_start: 0, parameters_count: 0, requires_start: 0, requires_count: 0, ensures_start: 0, ensures_count: 0, pure: false, verified: false, verification_reason: ""})

        def test_threaded_statement(report: ProofReport&, owner: sview, owner_line: u32, line: u32) -> (known: bool, statement: Ast::Stmt):
            body: mutable darray[Ast::Stmt] = []
            matches: mutable usize = 0
            proof_replay_local_binding_find_owner(report.source_declarations, owner, owner_line, &body, &matches, 0)
            return (false, Ast::Stmt.Invalid) if matches != 1
            for statement in body |line|:
                match statement:
                    Ast::Stmt.Expr(_, position):
                        return (true, statement) if position.line == line
                    _:
                        pass
            return (false, Ast::Stmt.Invalid)

        def test_threaded_call(statement: Ast::Stmt) -> Ast::Expr:
            match statement:
                Ast::Stmt.Expr(expression, _):
                    return proof_strip_parens(expression)
                _:
                    return Ast::Expr.Invalid

        def test_threaded_valid(report: mutable ProofReport&, owner_line: u32, trace: ProofFactTrace, summary: ProofExecutableSummary, call: Ast::Expr) -> bool:
            report.replay_owner_line <- owner_line
            report.trace_owner_line <- trace.line
            threading: ProofReplayThreading = proof_replay_summary_threading(report, trace, summary, call)
            return threading.valid and threading.symbols.count > 0

        def test_threaded_live(report: mutable ProofReport&, owner: sview, owner_line: u32, statement: Ast::Stmt, local_name: sview) -> bool:
            report.replay_owner_line <- owner_line
            return proof_replay_thread_call_resymbolized(report, owner, statement, local_name)

        # A copy of the honest bindings with the threaded symbol replaced by `symbol`.
        def test_threaded_rebound(report: mutable ProofReport&, trace: ProofFactTrace, symbol: sview) -> ProofFactTrace:
            start: usize = report.traces.summary_values.count
            for offset in 0..<trace.summary_bindings_count |offset, report, trace, symbol|:
                name_copy: sview = report.traces.summary_names[trace.summary_bindings_start + offset]
                value_copy: Ast::Expr = report.traces.summary_values[trace.summary_bindings_start + offset]
                report.traces.summary_names.push(name_copy)
                report.traces.summary_values.push(Ast::Expr.Ident(symbol, Ast::expr_pos(value_copy)) if name_copy == "__threaded_state" else value_copy)
            return test_threaded_retrace(trace, trace.name, trace.line, start, trace.summary_bindings_count)

        def test_threaded_symbol(report: ProofReport&, trace: ProofFactTrace) -> sview:
            for offset in 0..<trace.summary_bindings_count |offset, report, trace|:
                slot: usize = trace.summary_bindings_start + offset
                if report.traces.summary_names[slot] == "__threaded_state":
                    match report.traces.summary_values[slot]:
                        Ast::Expr.Ident(symbol, _):
                            return symbol
                        _:
                            return ""
            return ""

        # `callee(arguments...)` at the honest call's position.
        def test_threaded_forged_call(call: Ast::Expr, callee_name: sview, arguments: darray[Ast::Expr]) -> Ast::Expr:
            match call:
                Ast::Expr.Call(callee, _, _, position):
                    names: mutable darray[sview] = []
                    for _ in arguments |names|:
                        names.push("")
                    return Ast::Expr.Call(Ast::Expr.Ident(callee_name, Ast::expr_pos(callee)), arguments, names, position)
                _:
                    return Ast::Expr.Invalid

        def test_threaded_lend(name: sview, position: Ast::Pos) -> Ast::Expr:
            return Ast::Expr.Unary(TokenKind.Ampersand, Ast::Expr.Ident(name, position), position)

        # A two-parameter threaded summary lending `x` to both parameters.
        def test_threaded_doubled(report: mutable ProofReport&, trace: ProofFactTrace, call: Ast::Expr, symbol: sview) -> ProofFactTrace:
            start: usize = report.traces.summary_values.count
            position: Ast::Pos = Ast::expr_pos(call)
            report.traces.summary_names.push("first")
            report.traces.summary_values.push(Ast::Expr.Ident("x", position))
            report.traces.summary_names.push("second")
            report.traces.summary_values.push(Ast::Expr.Ident("x", position))
            report.traces.summary_names.push("result")
            report.traces.summary_values.push(call)
            report.traces.summary_names.push("__threaded_state")
            report.traces.summary_values.push(Ast::Expr.Ident(symbol, position))
            report.traces.summary_names.push("__threaded_state")
            report.traces.summary_values.push(Ast::Expr.Ident("__elisa_rebind_7", position))
            return test_threaded_retrace(trace, trace.name, trace.line, start, 5)

using Ast
using ElisaProof

def test_threaded_check(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    proof_check(file, report)

# 0: stop at the first failure; 1: run every probe and report accepted forgeries as 64 + mask.
const HOLES_MODE: i64 = HOLES_MODE_PLACEHOLDER

def test_threaded_forged(accepted: bool, bit: i64, forged: mutable i64&) -> i64:
    return 0 if not accepted
    return 100 + bit if HOLES_MODE == 0
    forged <- forged + bit if (forged / bit) % 2 == 0
    return 0

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    text: sview = "SOURCE_TEXT_PLACEHOLDER"
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    test_threaded_check(text, &source, &report)
    forged: mutable i64 = 0
    stop: mutable i64 = 0

    honest_index: usize = test_threaded_summary(&report, "lent", 9)
    return 1 if honest_index >= report.traces.records.count
    honest: ProofFactTrace = report.traces.records[honest_index]
    bump: (known: bool, summary: ProofExecutableSummary) = test_threaded_executable(&report, "bump")
    unsafe_bump: (known: bool, summary: ProofExecutableSummary) = test_threaded_executable(&report, "bump_unsafe")
    keep: (known: bool, summary: ProofExecutableSummary) = test_threaded_executable(&report, "keep")
    peek: (known: bool, summary: ProofExecutableSummary) = test_threaded_executable(&report, "peek")
    both: (known: bool, summary: ProofExecutableSummary) = test_threaded_executable(&report, "bump_both")
    return 2 if not bump.known or not unsafe_bump.known or not keep.known or not peek.known or not both.known
    site: (known: bool, statement: Ast::Stmt) = test_threaded_statement(&report, "lent", 7, 9)
    return 3 if not site.known
    call: Ast::Expr = test_threaded_call(site.statement)
    symbol: sview = test_threaded_symbol(&report, honest)
    return 4 if symbol == ""

    # The honest summary validates and keeps x's own symbol alive across the call.
    return 5 if not test_threaded_valid(&report, 7, honest, bump.summary, call)
    return 6 if not test_threaded_live(&report, "lent", 7, site.statement, "x")

    # S must be a rebind symbol.
    plain: ProofFactTrace = test_threaded_rebound(&report, honest, "x")
    stop <- test_threaded_forged(test_threaded_valid(&report, 7, plain, bump.summary, call), 1, &forged)
    return stop if stop != 0

    # S must not also be defined by a local binding.
    defined: mutable ProofReport = proof_empty_report()
    defined_source: mutable darray[u8] = []
    test_threaded_check(text, &defined_source, &defined)
    defined_trace: ProofFactTrace = defined.traces.records[test_threaded_summary(&defined, "lent", 9)]
    position: Ast::Pos = Ast::expr_pos(call)
    binding: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(symbol, position), TokenKind.EqEq, Ast::Expr.IntLit(9, position), position)
    defined.traces.records.push(ProofFactTrace{expression: binding, kernel_expression: 0, kind: "local-binding", line: 9, name: "lent", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0})
    stop <- test_threaded_forged(test_threaded_valid(&defined, 7, defined_trace, bump.summary, call), 2, &forged)
    return stop if stop != 0

    # A callee with an Unsafe effect, a region parameter or a read-only reference parameter.
    unsafe_call: Ast::Expr = test_threaded_forged_call(call, "bump_unsafe", [test_threaded_lend("x", position)])
    stop <- test_threaded_forged(test_threaded_valid(&report, 7, honest, unsafe_bump.summary, unsafe_call), 4, &forged)
    return stop if stop != 0
    keep_call: Ast::Expr = test_threaded_forged_call(call, "keep", [test_threaded_lend("x", position)])
    stop <- test_threaded_forged(test_threaded_valid(&report, 7, honest, keep.summary, keep_call), 8, &forged)
    return stop if stop != 0
    peek_call: Ast::Expr = test_threaded_forged_call(call, "peek", [test_threaded_lend("x", position)])
    stop <- test_threaded_forged(test_threaded_valid(&report, 7, honest, peek.summary, peek_call), 16, &forged)
    return stop if stop != 0

    # The lent place must be a non-reference local of the owner: not a global or other name, and
    # not a reference local (whose call is not threaded, so x's binding ends there).
    global_call: Ast::Expr = test_threaded_forged_call(call, "bump", [test_threaded_lend("counter", position)])
    stop <- test_threaded_forged(test_threaded_valid(&report, 7, honest, bump.summary, global_call), 32, &forged)
    return stop if stop != 0
    reference_site: (known: bool, statement: Ast::Stmt) = test_threaded_statement(&report, "via_ref", 25, 28)
    return 7 if not reference_site.known
    via_reference: ProofFactTrace = test_threaded_retrace(honest, "via_ref", 28, honest.summary_bindings_start, honest.summary_bindings_count)
    stop <- test_threaded_forged(test_threaded_valid(&report, 25, via_reference, bump.summary, test_threaded_call(reference_site.statement)), 64, &forged)
    return stop if stop != 0
    stop <- test_threaded_forged(test_threaded_live(&report, "via_ref", 25, reference_site.statement, "x"), 128, &forged)
    return stop if stop != 0

    # One local lent to two threaded parameters.
    doubled_call: Ast::Expr = test_threaded_forged_call(call, "bump_both", [test_threaded_lend("x", position), test_threaded_lend("x", position)])
    doubled: ProofFactTrace = test_threaded_doubled(&report, honest, doubled_call, symbol)
    stop <- test_threaded_forged(test_threaded_valid(&report, 7, doubled, both.summary, doubled_call), 256, &forged)
    return stop if stop != 0
    return 64 + forged if HOLES_MODE == 1
    return 0
'''


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="threaded-summary-holes-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "threaded_summary_holes.elisa"
        executable = directory / "threaded_summary_holes"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        escaped = SOURCE_TEXT.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        harness = (
            HARNESS.replace("../../Elisa-compiler/", compiler_include)
            .replace('include "../src/', 'include "../../src/')
            .replace("SOURCE_TEXT_PLACEHOLDER", escaped)
            .replace("HOLES_MODE_PLACEHOLDER", os.environ.get("ELISA_REPLAY_HOLES_MODE", "0"))
        )
        source.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", "-O2", "-o", str(executable), str(source)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=int(os.environ.get("ELISA_HARNESS_COMPILE_TIMEOUT", "300")),
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 harness compile failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=120)
        if os.environ.get("ELISA_REPLAY_HOLES_MODE", "0") != "0":
            print(f"mode {os.environ['ELISA_REPLAY_HOLES_MODE']} exit {result.returncode}")
            return
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)

    print("replay threaded-summary holes: plain or locally bound exit symbols, unsafe, region-bound or read-only callees, non-local or reference-local lends and a doubly lent local fail; the honest threaded call replays")


if __name__ == "__main__":
    main()
