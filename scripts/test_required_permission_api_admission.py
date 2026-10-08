"""Required permissions cannot be discharged by warning compatibility severity."""
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
valid = "def checked() -> bool:\n    ensure result == true\n    true\n"
invalid = ('def checked() -> bool:\n    ensure result == true\n    true\n\ndef f() -> void:\n    panic("boom")\n', 'def checked() -> bool:\n    ensure result == true\n    true\n\nextern emit(value: int) -> void can[Console.Write]\n\ndef caller() -> void:\n    emit(1)\n', 'def checked() -> bool:\n    ensure result == true\n    true\n\ndef h() -> void:\n    can Abort.Panic:\n        panic("x")\n\ndef caller() -> void:\n    h()\n', 'def checked() -> bool:\n    ensure result == true\n    true\n\nextern emit(value: int) -> void can[Console.Write]\n\ndef caller() -> void:\n    callee()\n\ndef callee() -> void:\n    emit(1) can Console.Write\n', 'def checked() -> bool:\n    ensure result == true\n    true\n\ndef g() -> void can[Abort.Panic]:\n    can Abort.Panic:\n        panic("x")\n\ndef caller() -> void:\n    g()\n')
constants = "const VALID_API_SOURCE: sview = " + json.dumps(valid) + "\n"
constants += "const REFINEMENT_API_SOURCE: sview = " + json.dumps('type Positive = i64 where self >= 0\ndef checked(value: Positive) -> i64:\n    ensure result >= 0\n    return value\n') + "\n"
constants += "const MUTUAL_API_SOURCE: sview = " + json.dumps((ROOT / "examples/mutual_structural_decreases.elisa").read_text().replace("structural_even", "checked")) + "\n"
constants += "const UNKNOWN_API_SOURCE: sview = " + json.dumps("def checked(value: bool) -> bool:\n    ensure result == true\n    value\n") + "\n"
constants += "const INVALID_API_SOURCES: sview[5] = [" + ", ".join(map(json.dumps, invalid)) + "]\n"
constants += "const GRANTED_API_SOURCES: sview[4] = [" + ", ".join(map(json.dumps, ('def checked() -> bool:\n    ensure result == true\n    true\n\ndef f() -> void:\n    can Abort.Panic:\n        panic("boom")\n', 'def checked() -> bool:\n    ensure result == true\n    true\n\nextern emit(value: int) -> void can[Console.Write]\ndef caller() -> void:\n    can Console.Write:\n        emit(1)\n', 'def checked() -> bool:\n    ensure result == true\n    true\n\ndef h() -> void:\n    can Abort.Panic:\n        panic("x")\ndef caller() -> void:\n    can Abort.Panic:\n        h()\n', 'def checked() -> bool:\n    ensure result == true\n    true\n\nextern emit(value: int) -> void can[Console.Write]\ndef caller() -> void:\n    can Console.Write:\n        callee()\ndef callee() -> void:\n    can Console.Write:\n        emit(1)\n'))) + "]\n"
harness = prefix + constants + r'''
extend ElisaProof:
    public:
        def proof_test_required_permission_kind(file: Ast::File&, report: mutable ProofReport&, kind: Semantic::DiagnosticKind) -> bool can Memory.Allocate, Abort.Panic:
            table: mutable Semantic::SymbolTable = Semantic::SymbolTable()
            table.diagnostics.push(Semantic::Diagnostic{kind: kind, line: 1})
            return proof_prepare_semantic_source_checked(file, report, table)

const REQUIRED_PERMISSION_KINDS: Semantic::DiagnosticKind[7] = [Semantic::DiagnosticKind.UngrantedPanic, Semantic::DiagnosticKind.UngrantedEffectCall, Semantic::DiagnosticKind.UngrantedPointerCast, Semantic::DiagnosticKind.UngrantedBufferReinterpret, Semantic::DiagnosticKind.UncheckedIndexUngranted, Semantic::DiagnosticKind.MutableAliasUngranted, Semantic::DiagnosticKind.UngrantedParallelFor]
def api_probe(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&, route: usize) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: mutable Ast::File = frontend_parse(&source[0])
    # Match the CLI's source-owned refinement preparation before calling the core API.
    refusals: mutable ProofReport = proof_empty_report()
    refined: mutable darray[sview] = []
    proof_add_refinement_signature_contracts(&file, &refusals, &refined)
    diagnostics.clear()
    if route == 0:
        proof_check(file, report)
    elif route == 1:
        proof_check_with_semantic_diagnostics(file, report, diagnostics)
    else:
        proof_check_focused_with_semantic_diagnostics(file, report, diagnostics, "checked")
    proof_replay_certificates(report)

def main() -> i64 can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    diagnostics: mutable darray[Semantic::Diagnostic] = []
    for index in 0..<7 |index, source, report, diagnostics|:
        api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, 0)
        file: Ast::File = frontend_parse(&source[0])
        return 180 if proof_test_required_permission_kind(file, &report, REQUIRED_PERMISSION_KINDS[index])
        return 181 if report.certificates.count != 0 or report.goal_attempts.count != 0 or report.proven != 0 or report.kernel.nodes.count != 0
        return 182 if not any finding in report.findings where finding.kind == "semantic-permission-ungranted"
    api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, 0)
    lint_file: Ast::File = frontend_parse(&source[0])
    return 183 if not proof_test_required_permission_kind(lint_file, &report, Semantic::DiagnosticKind.UnusedLocal)
    for route in 0..<3 |route, source, report, diagnostics|:
        for index in 0..<5 |index, route, source, report, diagnostics|:
            api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route)
            return 170 if report.certificates.count == 0 or report.proven == 0
            api_probe(INVALID_API_SOURCES[index], &source, &report, &diagnostics, route)
            return 171 if report.certificates.count != 0 or report.goal_attempts.count != 0 or report.proven != 0
            return 172 if report.source_declarations.count != 0 or report.traces.records.count != 0 or report.kernel.nodes.count != 0
            expected_kind: sview = "semantic-permission-ungranted"
            return 173 if not any finding in report.findings where finding.kind == expected_kind
            if route != 0:
                return 174 if not any diagnostic in diagnostics where diagnostic.kind == Semantic::DiagnosticKind.UngrantedPanic or diagnostic.kind == Semantic::DiagnosticKind.UngrantedEffectCall
        api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route)
        return 175 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
        for index in 0..<4 |index, route, source, report, diagnostics|:
            api_probe(GRANTED_API_SOURCES[index], &source, &report, &diagnostics, route)
            return 179 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
        api_probe(REFINEMENT_API_SOURCE, &source, &report, &diagnostics, route)
        return 190 if report.certificates.count == 0
        return 191 if report.proven == 0
        return 192 if report.failed != 0
        return 193 if report.replay_gaps != 0
        api_probe(MUTUAL_API_SOURCE, &source, &report, &diagnostics, route)
        return 177 if report.failed != 0 or report.structural.verified_names.count == 0 or report.replay_gaps != 0
        api_probe(UNKNOWN_API_SOURCE, &source, &report, &diagnostics, route)
        return 178 if report.failed == 0 and report.proven == report.obligations
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Required permission API admission: five ungranted source forms clear reused proof state on three APIs; granted and legacy proof controls replay")
