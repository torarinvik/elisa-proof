"""Entry-count snapshots replay only while source count and intrinsic ownership remain valid."""
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
baseline = """def checked(v: mutable darray[u32]&) -> usize:
    requires v.count > 0
    ensures result == old(v.count)
    return v.count
"""
mutants = (
    baseline.replace("    return v.count", "    v.pop()\n    return v.count"),
    baseline.replace("    return v.count", "    mutate(v)\n    return v.count")
    + "\ndef mutate(v: mutable darray[u32]&) -> void:\n    v.pop()\n",
    baseline + "\ndef old(value: usize) -> usize:\n    return value\n",
    baseline.replace("v: mutable darray[u32]&", "v: mutable darray[u32]&, old: usize"),
    baseline.replace("old(v.count)", "mutate(v)")
    + "\ndef mutate(v: mutable darray[u32]&) -> usize:\n    v.pop()\n    return v.count\n",
)
nested = baseline.replace("    return v.count", "    v[0] <- 7\n    return v.count")
constants = "const CAN_BINDING_SOURCE: sview = " + json.dumps(baseline) + "\n"
constants += "const CAN_NESTED_SOURCE: sview = " + json.dumps(nested) + "\n"
constants += "const CAN_STALE_SOURCES: sview[5] = [" + ", ".join(map(json.dumps, mutants)) + "]\n"
harness = prefix + constants + r'''
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
    for index in 0..<5 |index, original, replaced, report|:
        can_test_replace_source(CAN_STALE_SOURCES[index], &replaced, &report)
        proof_replay_certificates(&report)
        return 211 if report.replay_gaps == 0
        can_test_replace_source(CAN_BINDING_SOURCE, &replaced, &report)
        proof_replay_certificates(&report)
        return 215 if report.replay_gaps != 0
    proof_test_parse_and_replay(CAN_NESTED_SOURCE, &original, &report)
    return 216 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Entry-count replay: unchanged and element-write counts replay; pop, mutable call, shadowed old and effectful contracts reject stale certificates")
