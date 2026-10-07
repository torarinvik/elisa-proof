"""Adversarial replay probes for literal-argument rebinds and call summaries over locals.

Each probe parses a small source, runs the checker, then forges the report the way a buggy or
hostile producer could and calls the replay validator directly under the consuming
certificate's context. Forgeries must be refused; the honest traces beside them must still be
accepted.

- Literal rebinds (`__elisa_rebind_N == lit`) are definitions: a symbol bound to two literals,
  or a definition consumed by a certificate at another call, is refused.
- A forged summary whose result value re-enters the rebind comparison (the
  literal-argument -> summary-site -> argument -> rebind cycle) fails closed without
  exhausting the stack.
- A summary restated over a local is accepted only at the exact binding statement whose value
  is that call, and only while no write (later assignment, branch or loop) can intervene before
  the consuming certificate.
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
    "def k(x: i64) -> i64:\n"  # 1
    "    requires x >= 0\n"  # 2
    "    ensure result == x\n"  # 3
    "    return x\n"  # 4
    "\n"  # 5
    "def two() -> i64:\n"  # 6
    "    a: i64 = k(5)\n"  # 7
    "    b: i64 = k(7)\n"  # 8
    "    return b\n"  # 9
    "\n"  # 10
    "def idu(x: u64) -> u64:\n"  # 11
    "    ensure result == x\n"  # 12
    "    return x\n"  # 13
    "\n"  # 14
    "def rewritten() -> u64:\n"  # 15
    "    y: mutable u64 = idu(5)\n"  # 16
    "    y <- idu(7)\n"  # 17
    "    return y\n"  # 18
    "\n"  # 19
    "def branchy(c: bool) -> u64:\n"  # 20
    "    y: mutable u64 = 0\n"  # 21
    "    if c:\n"  # 22
    "        y <- idu(7)\n"  # 23
    "    return y\n"  # 24
    "\n"  # 25
    "def straight() -> u64:\n"  # 26
    "    y: u64 = idu(9)\n"  # 27
    "    return y\n"  # 28
    "\n"  # 29
    "def looped(n: u64) -> u64:\n"  # 30
    "    y: mutable u64 = idu(1)\n"  # 31
    "    j: mutable u64 = 0\n"  # 32
    "    while j < n:\n"  # 33
    "        j <- j + 1\n"  # 34
    "        y <- idu(2)\n"  # 35
    "    return y\n"  # 36
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
        def test_holes_trace_with(trace: ProofFactTrace, expression: Ast::Expr, bindings_start: usize) -> ProofFactTrace:
            return ProofFactTrace{expression: expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}

        def test_holes_binding_valid(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            return proof_replay_local_binding_source_valid(report, trace)

        def test_holes_literal_source(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            return proof_replay_local_binding_literal_call_argument_source(report, trace)

        def test_holes_context(report: mutable ProofReport&, owner_line: u32, consumer_line: u32, certificate: usize) -> void:
            report.replay_owner_line <- owner_line
            report.trace_owner_line <- consumer_line
            report.trace_consumer_certificate_index <- certificate

        # One plus the index of the first certificate of `owner` at `line`; 0 when none.
        def test_holes_certificate(report: ProofReport&, owner: sview, line: u32) -> usize:
            for index in 0..<report.certificates.count |index, report, owner, line|:
                return index + 1 if report.certificates[index].name == owner and report.certificates[index].line == line
            return 0

        def test_holes_rebind_binding(report: ProofReport&, owner: sview, line: u32) -> usize:
            for index in 0..<report.traces.records.count |index, report, owner, line|:
                trace: ProofFactTrace = report.traces.records[index]
                continue if trace.kind != "local-binding" or trace.name != owner or trace.line != line
                match trace.expression:
                    Ast::Expr.Binary(Ast::Expr.Ident(symbol, _), TokenKind.EqEq, _, _):
                        return index if proof_internal_name_is_rebind(symbol)
                    _:
                        pass
            return report.traces.records.count

        def test_holes_bound_symbol(trace: ProofFactTrace) -> sview:
            match trace.expression:
                Ast::Expr.Binary(Ast::Expr.Ident(symbol, _), TokenKind.EqEq, _, _):
                    return symbol
                _:
                    return ""

        def test_holes_summary_trace(report: ProofReport&, owner: sview, line: u32, dependency: sview) -> usize:
            for index in 0..<report.traces.records.count |index, report, owner, line, dependency|:
                trace: ProofFactTrace = report.traces.records[index]
                continue if trace.kind != "function-summary" or trace.name != owner or trace.line != line or trace.dependency != dependency
                continue if trace.summary_ensure_index != 0 or trace.summary_bindings_count != 2
                match report.traces.summary_values[trace.summary_bindings_start + 1]:
                    Ast::Expr.Call(_, _, _, _):
                        return index
                    _:
                        pass
            return report.traces.records.count

        def test_holes_executable(report: ProofReport&, name: sview) -> (known: bool, summary: ProofExecutableSummary):
            for candidate in report.executables.summaries |candidate, name|:
                return (true, candidate) if candidate.name == name
            return (false, ProofExecutableSummary{name: "", line: 0, parameters_start: 0, parameters_count: 0, requires_start: 0, requires_count: 0, ensures_start: 0, ensures_count: 0, pure: false, verified: false, verification_reason: ""})

        # Rename one rebind symbol in the bindings and summary values recorded at `line`.
        def test_holes_rename(report: mutable ProofReport&, owner: sview, line: u32, old_symbol: sview, new_symbol: sview) -> void:
            for index in 0..<report.traces.records.count |index, report, owner, line, old_symbol, new_symbol|:
                trace: ProofFactTrace = report.traces.records[index]
                continue if trace.name != owner or trace.line != line
                if trace.kind == "local-binding":
                    match trace.expression:
                        Ast::Expr.Binary(Ast::Expr.Ident(symbol, symbol_position), TokenKind.EqEq, value, position):
                            if symbol == old_symbol:
                                renamed: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(new_symbol, symbol_position), TokenKind.EqEq, value, position)
                                report.traces.records[index] <- test_holes_trace_with(trace, renamed, trace.summary_bindings_start)
                        _:
                            pass
                if trace.kind == "function-summary":
                    for offset in 0..<trace.summary_bindings_count |offset, report, trace, old_symbol, new_symbol|:
                        slot: usize = trace.summary_bindings_start + offset
                        match report.traces.summary_values[slot]:
                            Ast::Expr.Ident(symbol, symbol_position):
                                report.traces.summary_values[slot] <- Ast::Expr.Ident(new_symbol, symbol_position) if symbol == old_symbol
                            _:
                                pass

        # A copy of the direct summary `direct` with `result` bound to `local` at `position`.
        def test_holes_alias_trace(report: mutable ProofReport&, direct: ProofFactTrace, result_slot: usize, local: sview, position: Ast::Pos) -> ProofFactTrace:
            start: usize = report.traces.summary_values.count
            for offset in 0..<direct.summary_bindings_count |offset, report, direct, result_slot, local, position|:
                name_copy: sview = report.traces.summary_names[direct.summary_bindings_start + offset]
                value_copy: Ast::Expr = report.traces.summary_values[direct.summary_bindings_start + offset]
                report.traces.summary_names.push(name_copy)
                report.traces.summary_values.push(Ast::Expr.Ident(local, position) if offset == result_slot else value_copy)
            return test_holes_trace_with(direct, direct.expression, start)

        def test_holes_alias_accepted(report: mutable ProofReport&, owner_line: u32, consumer_line: u32, trace: ProofFactTrace, summary: ProofExecutableSummary) -> bool:
            test_holes_context(report, owner_line, consumer_line, 0)
            return proof_replay_summary_source_call(report, trace, summary).known

        def test_holes_write_at(body: darray[Ast::Stmt]&, line: u32, position: mutable Ast::Pos&, found: mutable bool&, depth: usize) -> void:
            return if depth >= 32
            for statement in body |line, position, found, depth|:
                match statement:
                    Ast::Stmt.VarDecl(_, _, _, statement_position):
                        if statement_position.line == line:
                            position <- statement_position
                            found <- true
                    Ast::Stmt.Assign(_, _, _, statement_position):
                        if statement_position.line == line:
                            position <- statement_position
                            found <- true
                    Ast::Stmt.If(_, yes, no, _):
                        test_holes_write_at(yes, line, position, found, depth + 1)
                        test_holes_write_at(no, line, position, found, depth + 1)
                    Ast::Stmt.While(_, inner, _):
                        test_holes_write_at(inner, line, position, found, depth + 1)
                    Ast::Stmt.Expr(Ast::Expr.Block(inner, _, _, _), _):
                        test_holes_write_at(inner, line, position, found, depth + 1)
                    _:
                        pass

        def test_holes_return_use_at(body: darray[Ast::Stmt]&, line: u32, name: sview, position: mutable Ast::Pos&, found: mutable bool&) -> void:
            for statement in body |line, name, position, found|:
                match statement:
                    Ast::Stmt.Return(value, statement_position):
                        if statement_position.line == line:
                            match value:
                                Ast::Expr.Ident(returned_name, use_position) if returned_name == name:
                                    position <- use_position
                                    found <- true
                                _:
                                    pass
                    _:
                        pass

        def test_holes_body(report: ProofReport&, owner: sview, owner_line: u32, body: mutable darray[Ast::Stmt]&) -> bool:
            matches: mutable usize = 0
            proof_replay_local_binding_find_owner(report.source_declarations, owner, owner_line, body, &matches, 0)
            return matches == 1

        def test_holes_statement_position(report: ProofReport&, owner: sview, owner_line: u32, line: u32) -> (known: bool, position: Ast::Pos):
            body: mutable darray[Ast::Stmt] = []
            position: mutable Ast::Pos = Ast::pos_at_line(line)
            found: mutable bool = false
            return (false, position) if not test_holes_body(report, owner, owner_line, &body)
            test_holes_write_at(body, line, &position, &found, 0)
            return (found, position)

        def test_holes_return_position(report: ProofReport&, owner: sview, owner_line: u32, line: u32, name: sview) -> (known: bool, position: Ast::Pos):
            body: mutable darray[Ast::Stmt] = []
            position: mutable Ast::Pos = Ast::pos_at_line(line)
            found: mutable bool = false
            return (false, position) if not test_holes_body(report, owner, owner_line, &body)
            test_holes_return_use_at(body, line, name, &position, &found)
            return (found, position)

        # A summary over `local` at the statement on `site_line` (or the return-use on that
        # line), copied from the direct summary of the call on `call_line`.
        def test_holes_alias(report: mutable ProofReport&, owner: sview, owner_line: u32, call_line: u32, site_line: u32, use_return: bool) -> (known: bool, trace: ProofFactTrace):
            direct_index: usize = test_holes_summary_trace(report, owner, call_line, "idu")
            empty: ProofFactTrace = ProofFactTrace{expression: Ast::Expr.Absent, kernel_expression: 0, kind: "", line: 0, name: "", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
            return (false, empty) if direct_index >= report.traces.records.count or report.traces.summary_names.count != report.traces.summary_values.count
            site: (known: bool, position: Ast::Pos) = test_holes_return_position(report, owner, owner_line, site_line, "y") if use_return else test_holes_statement_position(report, owner, owner_line, site_line)
            return (false, empty) if not site.known
            direct: ProofFactTrace = report.traces.records[direct_index]
            return (true, test_holes_alias_trace(report, direct, 1, "y", site.position))

using Ast
using ElisaProof

def test_holes_check(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    proof_check(file, report)

# 0: stop at the first failure; 1: run every probe and report accepted forgeries as 64 + mask
# (used to show each probe catches its hole on an unfixed tree); 2: only the cyclic probe.
const HOLES_MODE: i64 = HOLES_MODE_PLACEHOLDER

# An exit code to stop with when a forgery was accepted, else 0 (recording it in mode 1).
def test_holes_forged(accepted: bool, bit: i64, forged: mutable i64&) -> i64:
    return 0 if not accepted
    return 100 + bit if HOLES_MODE == 0
    forged <- forged + bit if (forged / bit) % 2 == 0
    return 0

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    text: sview = "SOURCE_TEXT_PLACEHOLDER"
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    test_holes_check(text, &source, &report)
    forged: mutable i64 = 0
    stop: mutable i64 = 0

    # Literal rebinds: each call's definition holds for that call's own certificates.
    b7: usize = test_holes_rebind_binding(&report, "two", 7)
    b8: usize = test_holes_rebind_binding(&report, "two", 8)
    return 1 if b7 >= report.traces.records.count or b8 >= report.traces.records.count
    c7: usize = test_holes_certificate(&report, "two", 7)
    c8: usize = test_holes_certificate(&report, "two", 8)
    return 2 if c7 == 0 or c8 == 0
    trace7: ProofFactTrace = report.traces.records[b7]
    trace8: ProofFactTrace = report.traces.records[b8]
    symbol7: sview = test_holes_bound_symbol(trace7)
    symbol8: sview = test_holes_bound_symbol(trace8)
    return 3 if symbol7 == "" or symbol8 == "" or symbol7 == symbol8

    if HOLES_MODE != 2:
        test_holes_context(&report, 6, 7, c7)
        return 4 if not test_holes_binding_valid(&report, trace7)
        test_holes_context(&report, 6, 8, c8)
        return 5 if not test_holes_binding_valid(&report, trace8)
        # The line-7 definition is not live in the line-8 call's certificate.
        stop <- test_holes_forged(test_holes_binding_valid(&report, trace7), 1, &forged)
        return stop if stop != 0

        # The same symbol bound to 5 at line 7 and to 7 at line 8 would prove 5 == 7.
        collided: mutable ProofReport = proof_empty_report()
        collided_source: mutable darray[u8] = []
        test_holes_check(text, &collided_source, &collided)
        test_holes_rename(&collided, "two", 8, symbol8, symbol7)
        collided7: ProofFactTrace = collided.traces.records[test_holes_rebind_binding(&collided, "two", 7)]
        collided8: ProofFactTrace = collided.traces.records[test_holes_rebind_binding(&collided, "two", 8)]
        return 6 if test_holes_bound_symbol(collided8) != symbol7
        test_holes_context(&collided, 6, 7, c7)
        stop <- test_holes_forged(test_holes_binding_valid(&collided, collided7), 2, &forged)
        return stop if stop != 0
        test_holes_context(&collided, 6, 8, c8)
        stop <- test_holes_forged(test_holes_binding_valid(&collided, collided8), 2, &forged)
        return stop if stop != 0

        # Summaries over a local.
        idu: (known: bool, summary: ProofExecutableSummary) = test_holes_executable(&report, "idu")
        return 20 if not idu.known
        declared: (known: bool, trace: ProofFactTrace) = test_holes_alias(&report, "rewritten", 15, 16, 16, false)
        return 21 if not declared.known
        return 22 if not test_holes_alias_accepted(&report, 15, 16, declared.trace, idu.summary)
        reassigned: (known: bool, trace: ProofFactTrace) = test_holes_alias(&report, "rewritten", 15, 17, 17, false)
        return 23 if not reassigned.known
        return 24 if not test_holes_alias_accepted(&report, 15, 18, reassigned.trace, idu.summary)
        straight: (known: bool, trace: ProofFactTrace) = test_holes_alias(&report, "straight", 26, 27, 28, true)
        return 25 if not straight.known
        return 26 if not test_holes_alias_accepted(&report, 26, 28, straight.trace, idu.summary)
        looped: (known: bool, trace: ProofFactTrace) = test_holes_alias(&report, "looped", 30, 31, 31, false)
        return 27 if not looped.known
        return 28 if not test_holes_alias_accepted(&report, 30, 31, looped.trace, idu.summary)
        # `idu(5)` attributed to the `y <- idu(7)` statement.
        misattributed: (known: bool, trace: ProofFactTrace) = test_holes_alias(&report, "rewritten", 15, 16, 17, false)
        return 29 if not misattributed.known
        stop <- test_holes_forged(test_holes_alias_accepted(&report, 15, 17, misattributed.trace, idu.summary), 4, &forged)
        return stop if stop != 0
        # The declaration's value consumed after `y <- idu(7)`.
        stop <- test_holes_forged(test_holes_alias_accepted(&report, 15, 18, declared.trace, idu.summary), 8, &forged)
        return stop if stop != 0
        # A return after a one-armed write: the branch may not have run.
        branch: (known: bool, trace: ProofFactTrace) = test_holes_alias(&report, "branchy", 20, 23, 24, true)
        return 30 if not branch.known
        stop <- test_holes_forged(test_holes_alias_accepted(&report, 20, 24, branch.trace, idu.summary), 16, &forged)
        return stop if stop != 0
        # A consumer inside a loop whose body later rewrites the local.
        stop <- test_holes_forged(test_holes_alias_accepted(&report, 30, 34, looped.trace, idu.summary), 32, &forged)
        return stop if stop != 0

    if HOLES_MODE != 1:
        # A result value spelled over the rebind symbol re-enters the literal comparison;
        # replay must answer instead of recursing until the stack is gone.
        cyclic: mutable ProofReport = proof_empty_report()
        cyclic_source: mutable darray[u8] = []
        test_holes_check(text, &cyclic_source, &cyclic)
        cyclic_summary: usize = test_holes_summary_trace(&cyclic, "two", 7, "k")
        return 10 if cyclic_summary >= cyclic.traces.records.count
        result_slot: usize = cyclic.traces.records[cyclic_summary].summary_bindings_start + 1
        match cyclic.traces.summary_values[result_slot]:
            Ast::Expr.Call(callee, arguments, names, position):
                return 11 if arguments.count != 1
                looped_arguments: darray[Ast::Expr] = [Ast::Expr.Ident(symbol7, position)]
                cyclic.traces.summary_values[result_slot] <- Ast::Expr.Call(callee, looped_arguments, names, position)
            _:
                return 12
        test_holes_context(&cyclic, 6, 7, c7)
        stop <- test_holes_forged(test_holes_literal_source(&cyclic, cyclic.traces.records[test_holes_rebind_binding(&cyclic, "two", 7)]), 64, &forged)
        return stop if stop != 0
    return 64 + forged if HOLES_MODE == 1
    return 0
'''


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="rebind-alias-holes-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "rebind_alias_holes.elisa"
        executable = directory / "rebind_alias_holes"
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

    print("replay rebind/alias holes: colliding or misplaced literal rebinds, a cyclic rebind summary, and stale, misattributed, branch-only or loop-rewritten local summaries fail; honest bindings replay")


if __name__ == "__main__":
    main()
