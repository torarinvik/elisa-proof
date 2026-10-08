"""Mutable assignment constant substitutions require source identity and reaching-state evidence."""
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
baseline = """const module Limits:
    const TOP: u8 = 10

def checked(x: u8) -> u8:
    requires x <= 5
    ensures result <= 15
    y: mutable u8 = x
    y <- x + Limits::TOP
    return y
"""
mutants = (
    baseline.replace("TOP: u8 = 10", "TOP: u8 = 20"),
    baseline.replace("y <- x + Limits::TOP", "y <- x - Limits::TOP"),
    baseline.replace("y <- x + Limits::TOP", "y <- x + Other::TOP")
    + "\nconst module Other:\n    const TOP: u8 = 10\n",
    baseline.replace("checked(x: u8)", "checked(Limits: u8, x: u8)"),
    baseline.replace("x: u8", "x: mutable u8"),
    baseline.replace("    return y", "    Limits: u8 = 10\n    return y"),
    baseline.replace("const TOP: u8 = 10", "global mutable TOP: u8 = 10"),
    baseline.replace("    return y", "    y <- 100\n    return y"),
    baseline.replace("checked(x: u8)", "checked(y: u8, x: u8)"),
)
nested = baseline.replace('x + Limits::TOP', 'Limits::TOP + x')
constants = "const CAN_BINDING_SOURCE: sview = " + json.dumps(baseline) + "\n"
constants += "const CAN_NESTED_SOURCE: sview = " + json.dumps(nested) + "\n"
constants += "const CAN_STALE_SOURCES: sview[9] = [" + ", ".join(map(json.dumps, mutants)) + "]\n"
harness = prefix + constants + r'''
extend ElisaProof:
    public:
        def proof_test_qualified_direct_source_gate(report: mutable ProofReport&) -> bool can Memory.Allocate, Abort.Panic:
            owner: mutable u32 = 0
            consumer: mutable u32 = 0
            for declaration in report.source_declarations |owner, consumer|:
                match declaration:
                    Ast::Decl.Func(name, _, _, body, _, _, position):
                        if name == "checked":
                            owner <- position.line
                            for statement in body |consumer|:
                                match statement:
                                    Ast::Stmt.Return(Ast::Expr.Ident(name, _), return_position):
                                        consumer <- return_position.line if name == "y"
                                    _:
                                        pass
                    _:
                        pass
            report.replay_owner_line <- owner
            report.trace_owner_line <- consumer
            for index in 0..<report.certificates.count |index, report|:
                if report.certificates[index].name == "checked" and report.certificates[index].rule == "goal":
                    report.trace_consumer_certificate_index <- index + 1
            for trace in report.traces.records |trace, report|:
                match trace.expression:
                    Ast::Expr.Binary(Ast::Expr.Ident(name, _), TokenKind.EqEq, _, _):
                        if trace.kind == "local-binding" and name == "y":
                            return true if proof_replay_local_binding_source_valid(report, trace)
                    _:
                        pass
            return false


def can_test_replace_source(text: sview, bytes: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    bytes.clear()
    for index in 0..<sview_len(text) |index, text, bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report.source_declarations <- file.top_decls
    consumer_line: mutable u32 = 0
    for declaration in file.top_decls |consumer_line|:
        match declaration:
            Ast::Decl.Func(name, _, _, body, _, _, _):
                if name == "checked":
                    for statement in body |consumer_line|:
                        match statement:
                            Ast::Stmt.Return(_, position):
                                consumer_line <- position.line
                            _:
                                pass
            _:
                pass
    for index in 0..<report.certificates.count |index, report, consumer_line|:
        if report.certificates[index].name == "checked" and report.certificates[index].rule == "goal":
            original: ProofGoalCertificate = report.certificates[index]
            report.certificates[index] <- ProofGoalCertificate{goal: original.goal, facts_start: original.facts_start, facts_count: original.facts_count, kernel_goal: original.kernel_goal, kernel_facts_start: original.kernel_facts_start, kernel_facts_count: original.kernel_facts_count, line: consumer_line, name: original.name, rule: original.rule, replayed: false}

def main() -> i64 can Memory.Allocate, Abort.Panic:
    original: mutable darray[u8] = []
    replaced: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(CAN_BINDING_SOURCE, &original, &report)
    return 210 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
    return 217 if not proof_test_qualified_direct_source_gate(&report)
    for index in 0..<9 |index, original, replaced, report|:
        can_test_replace_source(CAN_STALE_SOURCES[index], &replaced, &report)
        return 218 if proof_test_qualified_direct_source_gate(&report)
        proof_replay_certificates(&report)
        return 211 if report.replay_gaps == 0
        can_test_replace_source(CAN_BINDING_SOURCE, &replaced, &report)
        return 219 if not proof_test_qualified_direct_source_gate(&report)
        proof_replay_certificates(&report)
        return 215 if report.replay_gaps != 0
    proof_test_parse_and_replay(CAN_NESTED_SOURCE, &original, &report)
    return 216 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
    return 220 if not proof_test_qualified_direct_source_gate(&report)
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Mutable qualified assignment: source-authenticated arithmetic replays; changed value/operator/module, shadows, mutable inputs and later writes refuse stale certificates")
