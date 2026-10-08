"""Pop scalar snapshots are authenticated from exact source entry contracts and lifetime."""
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
baseline = """def checked(v: mutable darray[u32]&) -> u32:
    requires v.count >= 2 and v[v.count - 1] == 9
    ensures result == 9 and v.count == old(v.count) - 1
    x: u32 = v.pop()
    return x
"""
mutants = (
    baseline.replace("v[v.count - 1] == 9", "v[v.count - 1] == 8"),
    baseline.replace("v.count >= 2 and ", ""),
    baseline.replace("    x: u32", "    v[0] <- 8\n    x: u32"),
    baseline.replace("    return x", "    x <- 8\n    return x"),
    baseline.replace("v.pop()", "v.peek()"),
    baseline + "\ndef pop(v: mutable darray[u32]&) -> u32:\n    return 7\n",
    baseline.replace("x: u32", "x: mutable u32"),
    baseline.replace("    x: u32", "    mutate(v)\n    x: u32")
    + "\ndef mutate(v: mutable darray[u32]&) -> void:\n    v.pop()\n",
)
nested = baseline.replace("old(v.count) - 1", "old(v.count) - 2").replace("    return x", "    v.pop()\n    return x")
constants = "const CAN_BINDING_SOURCE: sview = " + json.dumps(baseline) + "\n"
constants += "const CAN_NESTED_SOURCE: sview = " + json.dumps(nested) + "\n"
constants += "const CAN_STALE_SOURCES: sview[8] = [" + ", ".join(map(json.dumps, mutants)) + "]\n"
harness = prefix + constants + r'''
extend ElisaProof:
    public:
        def proof_test_pop_direct_source_gate(report: mutable ProofReport&) -> bool can Memory.Allocate, Abort.Panic:
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
                                        consumer <- return_position.line if name == "x"
                                    _:
                                        pass
                    _:
                        pass
            report.replay_owner_line <- owner
            report.trace_owner_line <- consumer
            for trace in report.traces.records |report, trace|:
                match trace.expression:
                    Ast::Expr.Binary(Ast::Expr.Ident(name, _), TokenKind.EqEq, Ast::Expr.IntLit(value, _), _):
                        if trace.kind == "proof-step" and name == "x" and value == 9:
                            return true if proof_replay_pop_scalar_snapshot_source(report, trace)
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
    return 217 if not proof_test_pop_direct_source_gate(&report)
    for index in 0..<8 |index, original, replaced, report|:
        can_test_replace_source(CAN_STALE_SOURCES[index], &replaced, &report)
        return 218 if proof_test_pop_direct_source_gate(&report)
        proof_replay_certificates(&report)
        return 211 if report.replay_gaps == 0
        can_test_replace_source(CAN_BINDING_SOURCE, &replaced, &report)
        return 219 if not proof_test_pop_direct_source_gate(&report)
        proof_replay_certificates(&report)
        return 215 if report.replay_gaps != 0
    proof_test_parse_and_replay(CAN_NESTED_SOURCE, &original, &report)
    return 216 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
    return 220 if not proof_test_pop_direct_source_gate(&report)
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Pop scalar replay: exact entry snapshots survive later pops; changed guards/values, earlier writes/calls, scalar havoc and ambiguous methods reject stale certificates")
