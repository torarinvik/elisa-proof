"""Adversarial replay probes for name scope and consumer context.

Each probe parses a small source, runs the checker, then forges the report the way a buggy or
hostile producer could and calls the replay validator directly under the consuming
certificate's context. Forgeries must be refused; the honest traces beside them must still be
accepted.

- A global-constant fact, or the constant normalization of a call argument, is refused when any
  local of the owner function (declaration, loop variable, ...) spells the constant's name.
- An immutable-declaration or widening-cast binding is refused when the target, or a name in
  its initializer, is redeclared anywhere in the body, not only at the top level.
- A local binding reached as the premise of a derived proof step is subject to the same
  liveness rule as a certificate's own fact, and a verdict memoized for one certificate is not
  reused for another.
- An entry-precondition trace is accepted only while it matches a leading source requires clause
  or a parameter refinement; changing the source contract invalidates its dependent certificate.
- A call summary's precondition goal must have been proven at that call, not merely be a goal
  with the same text proven at another call.
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
    "const limit: i64 = 100\n"  # 1
    "\n"  # 2
    "def idc(x: i64) -> i64:\n"  # 3
    "    ensure result == x\n"  # 4
    "    return x\n"  # 5
    "\n"  # 6
    "def shadowed(value: i64) -> i64:\n"  # 7
    "    limit: i64 = value\n"  # 8
    "    y: i64 = idc(limit)\n"  # 9
    "    return y\n"  # 10
    "\n"  # 11
    "def plain() -> i64:\n"  # 12
    "    y: i64 = idc(limit)\n"  # 13
    "    return y\n"  # 14
    "\n"  # 15
    "def looped_shadow(value: i64) -> i64:\n"  # 16
    "    total: mutable i64 = 0\n"  # 17
    "    for limit in 0..<3:\n"  # 18
    "        total <- total + 1\n"  # 19
    "    return idc(limit)\n"  # 20
    "\n"  # 21
    "def nested(a: i64) -> i64:\n"  # 22
    "    t: i64 = a + 1\n"  # 23
    "    total: mutable i64 = 0\n"  # 24
    "    for t in 0..<3:\n"  # 25
    "        total <- total + t\n"  # 26
    "    return t\n"  # 27
    "\n"  # 28
    "def nested_ok(a: i64) -> i64:\n"  # 29
    "    t: i64 = a + 1\n"  # 30
    "    return t\n"  # 31
    "\n"  # 32
    "def inner_shadow(a: i64) -> i64:\n"  # 33
    "    t: i64 = a + 1\n"  # 34
    "    if t > 0:\n"  # 35
    "        a: i64 = 5\n"  # 36
    "        return t + a\n"  # 37
    "    return t\n"  # 38
    "\n"  # 39
    "def widen(narrow: i32) -> i64:\n"  # 40
    "    w: i64 = narrow.i64()\n"  # 41
    "    total: mutable i64 = 0\n"  # 42
    "    for w in 0..<3:\n"  # 43
    "        total <- total + w\n"  # 44
    "    return w\n"  # 45
    "\n"  # 46
    "def widen_ok(narrow: i32) -> i64:\n"  # 47
    "    w: i64 = narrow.i64()\n"  # 48
    "    return w\n"  # 49
    "\n"  # 50
    "def bounded_counter(bound: usize) -> usize:\n"  # 51
    "    rounds: mutable usize = 0\n"  # 52
    "    while rounds < bound:\n"  # 53
    "        invariant rounds <= bound\n"  # 54
    "        rounds <- rounds + 1\n"  # 55
    "    return rounds\n"  # 56
    "\n"  # 57
    "def pos(x: i64) -> i64:\n"  # 58
    "    requires x > 0\n"  # 59
    "    ensure result > 0\n"  # 60
    "    return x\n"  # 61
    "\n"  # 62
    "def caller(n: i64) -> i64:\n"  # 63
    "    requires n > 0\n"  # 64
    "    a: i64 = pos(n)\n"  # 65
    "    b: i64 = pos(n)\n"  # 66
    "    return b\n"  # 67
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
        def test_scope_trace(expression: Ast::Expr, kind: sview, line: u32, name: sview, owner_line: u32) -> ProofFactTrace:
            return ProofFactTrace{expression: expression, kernel_expression: 0, kind: kind, line: line, name: name, dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: owner_line}

        def test_scope_build_index(report: mutable ProofReport&) -> void:
            proof_replay_build_fact_trace_index(report)

        def test_scope_context(report: mutable ProofReport&, owner_line: u32, consumer_line: u32, certificate: usize) -> void:
            report.replay_owner_line <- owner_line
            report.trace_owner_line <- consumer_line
            report.trace_consumer_certificate_index <- certificate

        # `limit == 100`, imported for `owner` (declared at `owner_line`).
        def test_scope_constant_fact(owner: sview, owner_line: u32) -> ProofFactTrace:
            position: Ast::Pos = Ast::pos_at_line(1)
            fact: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("limit", position), TokenKind.EqEq, Ast::Expr.IntLit(100, position), position)
            return test_scope_trace(fact, "global-constant", 1, owner, owner_line)

        def test_scope_constant_valid(report: mutable ProofReport&, owner: sview, owner_line: u32) -> bool:
            test_scope_context(report, owner_line, owner_line, 0)
            return proof_replay_global_constant_fact_is_valid(report, test_scope_constant_fact(owner, owner_line))

        def test_scope_constant_normalized(report: mutable ProofReport&, owner: sview, owner_line: u32, use_line: u32) -> bool:
            test_scope_context(report, owner_line, use_line, 0)
            position: Ast::Pos = Ast::pos_at_line(use_line)
            caller: ProofFactTrace = test_scope_trace(Ast::Expr.Absent, "function-summary", use_line, owner, 0)
            return proof_replay_summary_call_global_constant_matches(report, caller, Ast::Expr.Ident("limit", position), Ast::Expr.IntLit(100, position))

        # The binding `target == initializer` (or `target == receiver` for a widening cast)
        # recorded at its declaration, consumed at `consumer_line`.
        def test_scope_declaration_trace(report: ProofReport&, owner: sview, owner_line: u32, target: sview, widening: bool) -> (known: bool, trace: ProofFactTrace):
            body: mutable darray[Ast::Stmt] = []
            matches: mutable usize = 0
            proof_replay_local_binding_find_owner(report.source_declarations, owner, owner_line, &body, &matches, 0)
            empty: ProofFactTrace = test_scope_trace(Ast::Expr.Absent, "local-binding", 0, owner, 0)
            return (false, empty) if matches != 1
            for statement in body |target, widening, owner|:
                match statement:
                    Ast::Stmt.VarDecl(name, _, initializer, position):
                        continue if name != target
                        value: mutable Ast::Expr = initializer
                        if widening:
                            match initializer:
                                Ast::Expr.Call(Ast::Expr.Field(receiver, _, _), _, _, _):
                                    value <- receiver
                                _:
                                    pass
                        expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(target, position), TokenKind.EqEq, value, position)
                        return (true, test_scope_trace(expression, "local-binding", position.line, owner, 0))
                    _:
                        pass
            return (false, empty)

        def test_scope_declaration_valid(report: mutable ProofReport&, owner: sview, owner_line: u32, target: sview, consumer_line: u32, widening: bool) -> i64:
            found: (known: bool, trace: ProofFactTrace) = test_scope_declaration_trace(report, owner, owner_line, target, widening)
            return 2 if not found.known
            test_scope_context(report, owner_line, consumer_line, 0)
            return 1 if widening and proof_replay_local_binding_widening_cast_declaration_source(report, found.trace)
            return 1 if not widening and proof_replay_local_binding_immutable_declaration_source(report, found.trace)
            return 0

        # One plus the index of a certificate of `owner` at `line` whose facts do (or do not)
        # include the loop guard; 0 when none.
        def test_scope_loop_certificate(report: ProofReport&, owner: sview, line: u32, with_guard: bool) -> usize:
            for index in 0..<report.certificates.count |index, report, owner, line, with_guard|:
                certificate: ProofGoalCertificate = report.certificates[index]
                continue if certificate.name != owner or certificate.line != line
                continue if certificate.facts_start > report.traces.origin_indices.count or certificate.facts_count > report.traces.origin_indices.count - certificate.facts_start
                guarded: mutable bool = false
                for offset in 0..<certificate.facts_count |offset, report, certificate, guarded|:
                    origin: usize = report.traces.origin_indices[certificate.facts_start + offset]
                    guarded <- true if origin < report.traces.records.count and report.traces.records[origin].kind == "loop-condition"
                return index + 1 if guarded == with_guard
            return 0

        def test_scope_binding_index(report: ProofReport&, owner: sview, line: u32) -> usize:
            for index in 0..<report.traces.records.count |index, report, owner, line|:
                trace: ProofFactTrace = report.traces.records[index]
                return index if trace.kind == "local-binding" and trace.name == owner and trace.line == line
            return report.traces.records.count

        # `P` derived from the single premise `P`.
        def test_scope_step_valid(report: mutable ProofReport&, step: ProofFactTrace, owner: sview, workspace: mutable ElisaProofKernelReplay::ProofKernelReplayValidationWorkspace&) -> bool:
            dependency_stack: darray[sview] = [owner]
            active_certificates: darray[usize] = []
            return proof_replay_fact_trace_is_valid_with_stack(report, step, owner, 0, dependency_stack, active_certificates, workspace)

        def test_scope_summary_index(report: ProofReport&, owner: sview, line: u32, dependency: sview) -> usize:
            for index in 0..<report.traces.records.count |index, report, owner, line, dependency|:
                trace: ProofFactTrace = report.traces.records[index]
                continue if trace.kind != "function-summary" or trace.name != owner or trace.line != line or trace.dependency != dependency
                continue if trace.summary_requires_count != 1 or trace.summary_bindings_count != 2
                match report.traces.summary_values[trace.summary_bindings_start + 1]:
                    Ast::Expr.Call(_, _, _, _):
                        return index
                    _:
                        pass
            return report.traces.records.count

        # A proven attempt of `owner` at `line` with the same goal text as attempt `like`.
        def test_scope_attempt(report: ProofReport&, owner: sview, line: u32, like: usize) -> usize:
            return report.goal_attempts.count if like >= report.goal_attempts.count
            goal: Ast::Expr = report.goal_attempts[like].goal
            for index in 0..<report.goal_attempts.count |index, report, owner, line, goal|:
                attempt: ProofGoalAttempt = report.goal_attempts[index]
                return index if attempt.name == owner and attempt.line == line and attempt.proven and attempt.has_certificate and proof_replay_expr_equal(attempt.goal, goal)
            return report.goal_attempts.count

        def test_scope_summary_valid(report: mutable ProofReport&, trace: ProofFactTrace, owner_line: u32, consumer_line: u32) -> bool:
            test_scope_context(report, owner_line, consumer_line, 0)
            dependency_stack: darray[sview] = [trace.name]
            active_certificates: darray[usize] = []
            workspace: mutable ElisaProofKernelReplay::ProofKernelReplayValidationWorkspace = ElisaProofKernelReplay::proof_kernel_replay_validation_workspace_new()
            return proof_replay_function_summary_is_valid(report, trace, dependency_stack, 0, active_certificates, &workspace)

        def test_scope_precondition_index(report: ProofReport&, owner: sview, owner_line: u32) -> usize:
            for index in 0..<report.traces.records.count |index, report, owner, owner_line|:
                trace: ProofFactTrace = report.traces.records[index]
                return index if trace.kind == "precondition" and trace.name == owner and trace.line == owner_line
            return report.traces.records.count

        def test_scope_mutate_precondition(report: mutable ProofReport&, owner: sview, owner_line: u32) -> bool:
            for index in 0..<report.source_declarations.count |index, report, owner, owner_line|:
                match report.source_declarations[index]:
                    Ast::Decl.Func(name, parameters, return_type, body, annotations, attributes, position):
                        continue if name != owner or position.line != owner_line
                        mutated_body: mutable darray[Ast::Stmt] = body
                        changed: mutable bool = false
                        for statement_index in 0..<mutated_body.count |statement_index, mutated_body, changed|:
                            match mutated_body[statement_index]:
                                Ast::Stmt.Contract("requires", _, contract_position):
                                    forged: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("x", contract_position), TokenKind.Lt, Ast::Expr.IntLit(0, contract_position), contract_position)
                                    mutated_body[statement_index] <- Ast::Stmt.Contract("requires", forged, contract_position)
                                    changed <- true
                                _:
                                    pass
                        report.source_declarations[index] <- Ast::Decl.Func(name, parameters, return_type, mutated_body, annotations, attributes, position)
                        return changed
                    _:
                        pass
            return false

using Ast
using ElisaProof

# 0: stop at the first failure; 1: run every probe and report accepted forgeries as 128 + mask
# (used to show each probe catches its hole on an unfixed tree).
const SCOPE_MODE: i64 = HOLES_MODE_PLACEHOLDER

# An exit code to stop with when a forgery was accepted, else 0 (recording it in mode 1).
def test_scope_forged(accepted: bool, bit: i64, forged: mutable i64&) -> i64:
    return 0 if not accepted
    return 100 + bit if SCOPE_MODE == 0
    forged <- forged + bit if (forged / bit) % 2 == 0
    return 0

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    text: sview = "SOURCE_TEXT_PLACEHOLDER"
    source: mutable darray[u8] = []
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    proof_replay_certificates(&report)
    forged: mutable i64 = 0
    stop: mutable i64 = 0

    # Global constants: a local spelled like the constant shadows it.
    return 1 if not test_scope_constant_valid(&report, "plain", 12)
    stop <- test_scope_forged(test_scope_constant_valid(&report, "shadowed", 7), 1, &forged)
    return stop if stop != 0
    stop <- test_scope_forged(test_scope_constant_valid(&report, "looped_shadow", 16), 1, &forged)
    return stop if stop != 0
    report.traces.records.push(test_scope_constant_fact("plain", 12))
    report.traces.records.push(test_scope_constant_fact("shadowed", 7))
    test_scope_build_index(&report)
    return 2 if not test_scope_constant_normalized(&report, "plain", 12, 13)
    stop <- test_scope_forged(test_scope_constant_normalized(&report, "shadowed", 7, 9), 2, &forged)
    return stop if stop != 0

    # Immutable and widening declarations: nested redeclarations of the target or its inputs.
    return 3 if test_scope_declaration_valid(&report, "nested_ok", 29, "t", 31, false) != 1
    nested_status: i64 = test_scope_declaration_valid(&report, "nested", 22, "t", 26, false)
    return 4 if nested_status == 2
    stop <- test_scope_forged(nested_status == 1, 4, &forged)
    return stop if stop != 0
    inner_status: i64 = test_scope_declaration_valid(&report, "inner_shadow", 33, "t", 37, false)
    return 5 if inner_status == 2
    stop <- test_scope_forged(inner_status == 1, 4, &forged)
    return stop if stop != 0
    return 6 if test_scope_declaration_valid(&report, "widen_ok", 47, "w", 49, true) != 1
    widen_status: i64 = test_scope_declaration_valid(&report, "widen", 40, "w", 44, true)
    return 7 if widen_status == 2
    stop <- test_scope_forged(widen_status == 1, 8, &forged)
    return stop if stop != 0

    # Loop-entry `rounds == 0` wrapped in a derived step, consumed by the preservation check.
    entry_certificate: usize = test_scope_loop_certificate(&report, "bounded_counter", 53, false)
    preservation_certificate: usize = test_scope_loop_certificate(&report, "bounded_counter", 53, true)
    return 8 if entry_certificate == 0 or preservation_certificate == 0
    binding_index: usize = test_scope_binding_index(&report, "bounded_counter", 52)
    return 9 if binding_index >= report.traces.records.count
    binding: ProofFactTrace = report.traces.records[binding_index]
    premises_start: usize = report.traces.premises.count
    report.traces.premises.push(binding.expression)
    step: ProofFactTrace = ProofFactTrace{expression: binding.expression, kernel_expression: 0, kind: "proof-step", line: 53, name: "bounded_counter", dependency: "", premises_start: premises_start, premises_count: 1, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0}
    shared: mutable ElisaProofKernelReplay::ProofKernelReplayValidationWorkspace = ElisaProofKernelReplay::proof_kernel_replay_validation_workspace_new()
    test_scope_context(&report, 51, 53, entry_certificate)
    return 10 if not test_scope_step_valid(&report, step, "bounded_counter", &shared)
    fresh: mutable ElisaProofKernelReplay::ProofKernelReplayValidationWorkspace = ElisaProofKernelReplay::proof_kernel_replay_validation_workspace_new()
    test_scope_context(&report, 51, 53, preservation_certificate)
    stop <- test_scope_forged(test_scope_step_valid(&report, step, "bounded_counter", &fresh), 16, &forged)
    return stop if stop != 0
    # The verdict memoized for the entry certificate must not answer for the preservation one.
    stop <- test_scope_forged(test_scope_step_valid(&report, step, "bounded_counter", &shared), 32, &forged)
    return stop if stop != 0

    # A precondition proven at the line-65 call does not discharge the line-66 call's.
    summary_index: usize = test_scope_summary_index(&report, "caller", 66, "pos")
    return 11 if summary_index >= report.traces.records.count
    summary_trace: ProofFactTrace = report.traces.records[summary_index]
    return 12 if not test_scope_summary_valid(&report, summary_trace, 63, 67)
    earlier_attempt: usize = test_scope_attempt(&report, "caller", 65, report.traces.summary_require_goal_ids[summary_trace.summary_requires_start])
    return 13 if earlier_attempt >= report.goal_attempts.count
    report.traces.summary_require_goal_ids[summary_trace.summary_requires_start] <- earlier_attempt
    stop <- test_scope_forged(test_scope_summary_valid(&report, summary_trace, 63, 67), 64, &forged)
    return stop if stop != 0

    # Entry assumptions must be bound to a leading source requires or a retained type refinement.
    precondition_index: usize = test_scope_precondition_index(report, "pos", 58)
    return 17 if precondition_index >= report.traces.records.count
    precondition_trace: ProofFactTrace = report.traces.records[precondition_index]
    test_scope_context(&report, 58, 60, 0)
    return 18 if not proof_replay_boundary_trace_shape_valid(report, precondition_trace)
    return 19 if not test_scope_mutate_precondition(&report, "pos", 58)
    return 20 if proof_replay_boundary_trace_shape_valid(report, precondition_trace)
    proof_replay_certificates(&report)
    return 21 if report.replay_gaps == 0
    return 128 + forged if SCOPE_MODE == 1
    return 0
'''


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    mode = os.environ.get("ELISA_REPLAY_HOLES_MODE", "0")
    with tempfile.TemporaryDirectory(prefix="scope-context-holes-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "scope_context_holes.elisa"
        executable = directory / "scope_context_holes"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        escaped = SOURCE_TEXT.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        harness = (
            HARNESS.replace("../../Elisa-compiler/", compiler_include)
            .replace('include "../src/', 'include "../../src/')
            .replace("SOURCE_TEXT_PLACEHOLDER", escaped)
            .replace("HOLES_MODE_PLACEHOLDER", mode)
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
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=300)
        if mode != "0":
            print(f"mode {mode} exit {result.returncode}")
            return
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)

    print("replay scope/context holes: source-bound entry preconditions, shadowed constants, nested redeclarations, stale loop bindings, and call-specific preconditions replay safely")


if __name__ == "__main__":
    main()
