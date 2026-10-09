"""Direct APIs gate semantic admission and bind parameter-return source goals."""
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
invalid = (
    valid + "\ndef missing_name() -> bool:\n    ensure result == true\n    undefined_value\n",
    valid + "\ndef missing_type(value: MissingType) -> bool:\n    ensure result == true\n    true\n",
    valid + "\ndef checked() -> bool:\n    ensure result == true\n    true\n",
)
invalid += tuple(valid + "\n" + source for source in (
    "def trap(raw: i64) -> i64:\n    return raw / 0\n",
    "def trap(raw: i64) -> i64:\n    return raw % 0\n",
    "def trap() -> i64:\n    value: i64 = 1\n    return value << 64\n",
    "def trap() -> i64:\n    value: i64 = 1\n    return value << -2\n",
))
invalid += (
    "global mutable api_counter: i64 = 0\ndef checked() -> i64:\n    return api_counter\n",
    "global mutable api_counter: i64 = 0\ndef checked() -> void:\n    api_counter <- 1\n",
    "global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Write]:\n    can Global{Write}:\n        return api_counter\n",
    "global mutable api_counter: i64 = 0\ndef checked() -> void can[Global.Read]:\n    can Global{Read}:\n        api_counter <- 1\n",
)
invalid += (
    "global mutable api_values: i64[1] = [0]\ndef checked(index: usize) -> i64 can[Global.Write]:\n    requires index < 1\n    can Global{Write}:\n        return api_values[index]\n",
    "global mutable api_values: i64[1] = [0]\ndef checked(index: usize) -> void can[Global.Read]:\n    requires index < 1\n    can Global{Read}:\n        api_values[index] <- 1\n",
    "global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Read]:\n    can Global{Read}:\n        borrowed: mutable i64& = &api_counter\n        return borrowed.i64()\n",
    "global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Write]:\n    can Global{Write}:\n        borrowed: mutable i64& = &api_counter\n        return borrowed.i64()\n",
)
constants = "const VALID_API_SOURCE: sview = " + json.dumps(valid) + "\n"
constants += "const REFINEMENT_API_SOURCE: sview = " + json.dumps('type Positive = i64 where self >= 0\ndef checked(value: Positive) -> i64:\n    ensure result >= 0\n    return value\n') + "\n"
constants += "const MUTUAL_API_SOURCE: sview = " + json.dumps((ROOT / "examples/mutual_structural_decreases.elisa").read_text().replace("structural_even", "checked")) + "\n"
constants += "const UNKNOWN_API_SOURCE: sview = " + json.dumps("def checked(value: bool) -> bool:\n    ensure result == true\n    value\n") + "\n"
constants += "const GLOBAL_READ_API_SOURCE: sview = " + json.dumps("global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Read]:\n    can Global{Read}:\n        return api_counter\n") + "\n"
constants += "const GLOBAL_WRITE_API_SOURCE: sview = " + json.dumps("global mutable api_counter: i64 = 0\ndef checked() -> void can[Global.Write]:\n    can Global{Write}:\n        api_counter <- 1\n") + "\n"
constants += "const GLOBAL_INDEXED_READ_API_SOURCE: sview = " + json.dumps("global mutable api_values: i64[1] = [0]\ndef checked(index: usize) -> i64 can[Global.Read]:\n    requires index < 1\n    can Global{Read}:\n        return api_values[index]\n") + "\n"
constants += "const GLOBAL_INDEXED_WRITE_API_SOURCE: sview = " + json.dumps("global mutable api_values: i64[1] = [0]\ndef checked(index: usize) -> void can[Global.Write]:\n    requires index < 1\n    can Global{Write}:\n        api_values[index] <- 1\n") + "\n"
constants += "const GLOBAL_MUTABLE_REFERENCE_API_SOURCE: sview = " + json.dumps("global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Read, Global.Write]:\n    can Global{Read,Write}:\n        borrowed: mutable i64& = &api_counter\n        return borrowed.i64()\n") + "\n"
constants += "const PARAMETER_RETURN_API_SOURCE: sview = " + json.dumps("def checked(value: i64) -> i64:\n    requires value == 7\n    ensure result == 7\n    return value\n") + "\n"
constants += "const PARAMETER_OPEN_API_SOURCE: sview = " + json.dumps("def checked(value: i64) -> i64:\n    ensure result == 7\n    return value\n") + "\n"
constants += "const INVALID_API_SOURCES: sview[15] = [" + ", ".join(map(json.dumps, invalid)) + "]\n"
harness = prefix + constants + r'''
def api_probe(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&, route: usize) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: mutable Ast::File = (frontend_parse(&source[0]) can Global{Read,Write})
    # Match the CLI's source-owned refinement preparation before calling the core API.
    refusals: mutable ProofReport = proof_empty_report()
    refined: mutable darray[sview] = []
    proof_add_refinement_signature_contracts(&file, &refusals, &refined)
    diagnostics.clear()
    if route == 0:
        (proof_check(file, report) can Global{Read,Write})
    elif route == 1:
        (proof_check_with_semantic_diagnostics(file, report, diagnostics) can Global{Read,Write})
    else:
        (proof_check_focused_with_semantic_diagnostics(file, report, diagnostics, "checked") can Global{Read,Write})
    (proof_replay_certificates(report) can Global{Read,Write})

def api_parameter_goal_attempt_index(report: ProofReport&) -> usize:
    for index in 0..<report.goal_attempts.count |index, report|:
        attempt: ProofGoalAttempt = report.goal_attempts[index]
        return index if attempt.name == "checked" and attempt.rule == "goal"
    return report.goal_attempts.count

def api_parameter_goal_probe(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&, route: usize, tamper: usize) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: mutable Ast::File = (frontend_parse(&source[0]) can Global{Read,Write})
    diagnostics.clear()
    if route == 0:
        (proof_check(file, report) can Global{Read,Write})
    elif route == 1:
        (proof_check_with_semantic_diagnostics(file, report, diagnostics) can Global{Read,Write})
    else:
        (proof_check_focused_with_semantic_diagnostics(file, report, diagnostics, "checked") can Global{Read,Write})
    (proof_replay_certificates(report) can Global{Read,Write})
    source_attempt_index: usize = api_parameter_goal_attempt_index(report)
    if tamper == 1:
        match report.source_declarations[0]:
            Ast::Decl.Func(name, parameters, return_type, body, annotations, attributes, position):
                mutated_body: mutable darray[Ast::Stmt] = body
                for index in 0..<mutated_body.count |index|:
                    match mutated_body[index]:
                        Ast::Stmt.Return(_, return_position):
                            mutated_body[index] <- Ast::Stmt.Return(Ast::Expr.IntLit(8, return_position), return_position)
                        _:
                            pass
                report.source_declarations[0] <- Ast::Decl.Func(name, parameters, return_type, mutated_body, annotations, attributes, position)
            _:
                pass
    elif tamper == 2:
        return if source_attempt_index >= report.goal_attempts.count
        original_attempt: ProofGoalAttempt = report.goal_attempts[source_attempt_index]
        contract_position: Ast::Pos = Ast::pos_at_line(3)
        forged_goal: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("other", contract_position), TokenKind.EqEq, Ast::Expr.IntLit(7, contract_position), contract_position)
        report.goal_attempts[source_attempt_index] <- ProofGoalAttempt{goal: forged_goal, budget_exhausted: original_attempt.budget_exhausted, facts_start: original_attempt.facts_start, facts_count: original_attempt.facts_count, kernel_goal: original_attempt.kernel_goal, kernel_facts_start: original_attempt.kernel_facts_start, kernel_facts_count: original_attempt.kernel_facts_count, line: original_attempt.line, name: original_attempt.name, rule: original_attempt.rule, proven: original_attempt.proven, has_certificate: original_attempt.has_certificate, certificate_index: original_attempt.certificate_index}
    elif tamper == 3:
        return if source_attempt_index >= report.goal_attempts.count
        source_attempt: ProofGoalAttempt = report.goal_attempts[source_attempt_index]
        return if not source_attempt.has_certificate or source_attempt.certificate_index >= report.certificates.count
        original_certificate: ProofGoalCertificate = report.certificates[source_attempt.certificate_index]
        contract_position: Ast::Pos = Ast::pos_at_line(3)
        forged_goal: Ast::Expr = Ast::Expr.Binary(Ast::Expr.IntLit(8, contract_position), TokenKind.EqEq, Ast::Expr.IntLit(7, contract_position), contract_position)
        report.certificates[source_attempt.certificate_index] <- ProofGoalCertificate{goal: forged_goal, facts_start: original_certificate.facts_start, facts_count: original_certificate.facts_count, kernel_goal: original_certificate.kernel_goal, kernel_facts_start: original_certificate.kernel_facts_start, kernel_facts_count: original_certificate.kernel_facts_count, line: original_certificate.line, name: original_certificate.name, rule: original_certificate.rule, replayed: original_certificate.replayed}

def main() -> i64 can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    diagnostics: mutable darray[Semantic::Diagnostic] = []
    for route in 0..<3 |route, source, report, diagnostics|:
        for index in 0..<15 |index, route, source, report, diagnostics|:
            (api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
            return 170 if report.certificates.count == 0 or report.proven == 0
            (api_probe(INVALID_API_SOURCES[index], &source, &report, &diagnostics, route) can Global{Read,Write})
            return 171 if report.certificates.count != 0 or report.goal_attempts.count != 0 or report.proven != 0
            return 172 if report.source_declarations.count != 0 or report.traces.records.count != 0 or report.kernel.nodes.count != 0
            expected_kind: sview = "semantic-source-inadmissible" if index < 3 or index >= 7 else "arithmetic-safety-refuted"
        return 173 if not any finding in report.findings where finding.kind == expected_kind
        if route != 0 and (index < 3 or index >= 7):
            return 174 if not any diagnostic in diagnostics where Semantic::diagnostic_severity(diagnostic) == 1
        if route != 0 and index >= 11:
            expected_global_effect: sview = "Global.Read" if index == 11 or index == 14 else "Global.Write"
            expected_global_name: sview = "api_values" if index == 11 or index == 12 else "api_counter"
            return 199 if not any diagnostic in diagnostics where diagnostic.expected == expected_global_effect and diagnostic.actual == expected_global_name and Semantic::diagnostic_severity(diagnostic) == 1
        (api_probe(GLOBAL_READ_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 194 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(GLOBAL_WRITE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 195 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(GLOBAL_INDEXED_READ_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 196 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(GLOBAL_INDEXED_WRITE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 197 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(GLOBAL_MUTABLE_REFERENCE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 198 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 175 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
        (api_probe(REFINEMENT_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 190 if report.certificates.count == 0
        return 191 if report.proven == 0
        return 192 if report.failed != 0
        return 193 if report.replay_gaps != 0
        (api_probe(MUTUAL_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 177 if report.failed != 0 or report.structural.verified_names.count == 0 or report.replay_gaps != 0
        (api_probe(UNKNOWN_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 178 if report.failed == 0 and report.proven == report.obligations
        (api_parameter_goal_probe(PARAMETER_RETURN_API_SOURCE, &source, &report, &diagnostics, route, 0) can Global{Read,Write})
        return 200 if report.failed != 0 or report.proven == 0 or report.replay_gaps != 0 or report.findings.count != 0
        return 210 if api_parameter_goal_attempt_index(report) >= report.goal_attempts.count
        return 201 if not proof_replay_certificates_complete(report) or not proof_report_source_admission_invariants_consistent(report)
        (api_parameter_goal_probe(PARAMETER_OPEN_API_SOURCE, &source, &report, &diagnostics, route, 0) can Global{Read,Write})
        return 202 if any finding in report.findings where finding.kind == "source-obligation-inventory"
        return 206 if not proof_report_has_open_goals(report)
        return 208 if report.failed != 1 or report.findings.count != 1
        return 209 if report.findings[0].kind != "ensure-unproven"
        return 203 if report.replay_gaps != 0 or not proof_report_source_admission_invariants_consistent(report)
        for tamper in 1..<4 |tamper, route, source, report, diagnostics|:
            (api_parameter_goal_probe(PARAMETER_RETURN_API_SOURCE, &source, &report, &diagnostics, route, tamper) can Global{Read,Write})
            return 204 if report.goal_attempts.count == 0 or report.certificates.count == 0
            return 205 if proof_report_source_admission_invariants_consistent(report)
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Direct API semantic admission: source-goal identity, Global grants, and reused-state clearing pass on all three routes")
