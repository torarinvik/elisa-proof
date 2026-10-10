"""Direct APIs gate semantic admission and bind source-owned proof obligations."""
import ast
import json
import os
from pathlib import Path
import re
from source_binding_harness_support import run_source_binding_replay_harness

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
prefix = next(ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "REPLAY_HARNESS"
                      for target in node.targets)).split("def main()")[0]
valid = "def checked() -> i64:\n    ensure result == 1\n    return 1\n"
invalid = (
    valid + "\ndef missing_name() -> bool:\n    ensure result == true\n    undefined_value\n",
    valid + "\ndef missing_type(value: MissingType) -> bool:\n    ensure result == true\n    true\n",
    valid + "\ndef checked() -> i64:\n    ensure result == 1\n    return 1\n",
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
    "global mutable api_values: i64[1] = [0]\nglobal mutable api_index: usize = 0\ndef checked() -> void can[Global.Write]:\n    can Global{Write}:\n        if api_index < 1:\n            api_values[api_index] <- 1\n",
    "global mutable api_values: i64[1] = [0]\nglobal mutable api_index: usize = 0\ndef checked() -> void can[Global.Read]:\n    can Global{Read}:\n        if api_index < 1:\n            api_values[api_index] <- 1\n",
)
invalid += (
    "module SharedState:\n    public:\n        global mutable api_counter: i64 = 0\ndef checked() -> i64:\n    return SharedState::api_counter\n",
    "module SharedState:\n    public:\n        global mutable api_counter: i64 = 0\ndef checked() -> void:\n    SharedState::api_counter <- 1\n",
)
global_grant_expectations = (
    ("Global.Read", "api_counter"),
    ("Global.Write", "api_counter"),
    ("Global.Read", "api_counter"),
    ("Global.Write", "api_counter"),
    ("Global.Read", "api_values"),
    ("Global.Write", "api_values"),
    ("Global.Write", "api_counter"),
    ("Global.Read", "api_counter"),
    ("Global.Read", "api_index"),
    ("Global.Write", "api_values"),
    ("Global.Read", "api_counter"),
    ("Global.Write", "api_counter"),
)
assert len(invalid) == 19 and len(global_grant_expectations) == len(invalid) - 7
constants = "const VALID_API_SOURCE: sview = " + json.dumps(valid) + "\n"
constants += "const REFINEMENT_API_SOURCE: sview = " + json.dumps('type Positive = i64 where self >= 0\ndef checked(value: Positive) -> i64:\n    ensure result >= 0\n    return value\n') + "\n"
constants += "const MUTUAL_API_SOURCE: sview = " + json.dumps((ROOT / "examples/mutual_structural_decreases.elisa").read_text().replace("structural_even", "checked")) + "\n"
constants += "const UNKNOWN_API_SOURCE: sview = " + json.dumps("def checked(value: bool) -> bool:\n    ensure result == true\n    value\n") + "\n"
constants += "const GLOBAL_READ_API_SOURCE: sview = " + json.dumps("global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Read]:\n    can Global{Read}:\n        return api_counter\n") + "\n"
constants += "const GLOBAL_WRITE_API_SOURCE: sview = " + json.dumps("global mutable api_counter: i64 = 0\ndef checked() -> void can[Global.Write]:\n    can Global{Write}:\n        api_counter <- 1\n") + "\n"
constants += "const GLOBAL_INDEXED_READ_API_SOURCE: sview = " + json.dumps("global mutable api_values: i64[1] = [0]\ndef checked(index: usize) -> i64 can[Global.Read]:\n    requires index < 1\n    can Global{Read}:\n        return api_values[index]\n") + "\n"
constants += "const GLOBAL_INDEXED_WRITE_API_SOURCE: sview = " + json.dumps("global mutable api_values: i64[1] = [0]\ndef checked(index: usize) -> void can[Global.Write]:\n    requires index < 1\n    can Global{Write}:\n        api_values[index] <- 1\n") + "\n"
constants += "const GLOBAL_MUTABLE_REFERENCE_API_SOURCE: sview = " + json.dumps("global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Read, Global.Write]:\n    can Global{Read,Write}:\n        borrowed: mutable i64& = &api_counter\n        return borrowed.i64()\n") + "\n"
constants += "const GLOBAL_MUTABLE_INDEX_API_SOURCE: sview = " + json.dumps("global mutable api_values: i64[1] = [0]\nglobal mutable api_index: usize = 0\ndef checked() -> void can[Global.Read, Global.Write]:\n    can Global{Read,Write}:\n        if api_index < 1:\n            api_values[api_index] <- 1\n") + "\n"
constants += "const GLOBAL_QUALIFIED_READ_API_SOURCE: sview = " + json.dumps("module SharedState:\n    public:\n        global mutable api_counter: i64 = 0\ndef checked() -> i64 can[Global.Read]:\n    can Global{Read}:\n        return SharedState::api_counter\n") + "\n"
constants += "const GLOBAL_QUALIFIED_WRITE_API_SOURCE: sview = " + json.dumps("module SharedState:\n    public:\n        global mutable api_counter: i64 = 0\ndef checked() -> void can[Global.Write]:\n    can Global{Write}:\n        SharedState::api_counter <- 1\n") + "\n"
constants += "const PARAMETER_RETURN_API_SOURCE: sview = " + json.dumps("def checked(value: i64) -> i64:\n    requires value == 7\n    ensure result == 7\n    return value\n") + "\n"
constants += "const PARAMETER_OPEN_API_SOURCE: sview = " + json.dumps("def checked(value: i64) -> i64:\n    ensure result == 7\n    return value\n") + "\n"
constants += "const SOURCE_ASSERT_BY_POSITIVE_API_SOURCE: sview = " + json.dumps((ROOT / "examples/source_obligation_assert_by_positive.elisa").read_text()) + "\n"
constants += "const SOURCE_ASSERT_BY_NESTED_API_SOURCE: sview = " + json.dumps((ROOT / "examples/source_obligation_assert_by_module.elisa").read_text()) + "\n"
constants += "const PARAMETER_TYPE_BOUND_API_SOURCE: sview = " + json.dumps("def checked(value: i64) -> i64:\n    requires value == 7\n    ensure result == 7\n    return value\n") + "\n"
constants += "const COUNTING_LOOP_TYPE_BOUND_API_SOURCE: sview = " + json.dumps("def checked() -> i64:\n    for index in 0..<3:\n        return index\n    return 0\n") + "\n"
constants += "const COUNTING_LOOP_TYPE_BOUND_SCOPE_API_SOURCE: sview = " + json.dumps("def checked() -> i64:\n    for index in 0..<3:\n        assert true by:\n            assert true\n    assert true by:\n        assert true\n    return 0\n") + "\n"
constants += "const LOOP_REBIND_TYPE_BOUND_API_SOURCE: sview = " + json.dumps("def checked(limit: usize) -> usize:\n    ensure result <= limit\n    rounds: mutable usize = 0\n    while rounds < limit |rounds, limit|:\n        invariant rounds <= limit\n        rounds <- rounds + 1\n    return rounds\n") + "\n"
constants += "const FIXED_ARRAY_TYPE_BOUND_API_SOURCE: sview = " + json.dumps("def checked(values: i64[1], index: usize) -> i64:\n    requires index < 1\n    return values[index]\n") + "\n"
constants += "const LOCAL_FIXED_ARRAY_TYPE_BOUND_API_SOURCE: sview = " + json.dumps("def checked(index: usize) -> i64:\n    requires index < 1\n    values: i64[1] = [7]\n    return values[index]\n") + "\n"
constants += "const LOCAL_SCALAR_TYPE_BOUND_API_SOURCE: sview = " + json.dumps("def checked() -> u8:\n    ensure result == 7\n    status: u8 = 7\n    return status\n") + "\n"
constants += "const FIXED_ARRAY_NO_BOUND_API_SOURCE: sview = " + json.dumps("def checked(values: i64[1], index: usize) -> i64:\n    return values[index]\n") + "\n"
constants += "const DYNAMIC_ARRAY_GUARD_API_SOURCE: sview = " + json.dumps("def checked(values: darray[i64]&, index: usize) -> i64:\n    requires index >= 0\n    if index >= values.count:\n        return 0\n    return values[index]\n") + "\n"
constants += "const DYNAMIC_ARRAY_SHADOWED_GUARD_API_SOURCE: sview = " + json.dumps("def checked(values: darray[i64]&, index: usize) -> i64:\n    requires index >= 0\n    values: darray[i64] = [7]\n    if index >= values.count:\n        return 0\n    return values[index]\n") + "\n"
constants += "const INVALID_API_SOURCES: sview[19] = [" + ", ".join(map(json.dumps, invalid)) + "]\n"
constants += "const INVALID_GLOBAL_GRANT_EXPECTED_EFFECTS: sview[12] = [" + ", ".join(map(json.dumps, (effect for effect, _ in global_grant_expectations))) + "]\n"
constants += "const INVALID_GLOBAL_GRANT_EXPECTED_GLOBALS: sview[12] = [" + ", ".join(map(json.dumps, (global_name for _, global_name in global_grant_expectations))) + "]\n"
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

def api_probe_before_replay(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&, route: usize) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: mutable Ast::File = (frontend_parse(&source[0]) can Global{Read,Write})
    diagnostics.clear()
    if route == 0:
        (proof_check(file, report) can Global{Read,Write})
    else:
        (proof_check_with_semantic_diagnostics(file, report, diagnostics) can Global{Read,Write})

def api_global_array_replay_probe(source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&, route: usize, tamper: usize) -> void can Memory.Allocate, Abort.Panic:
    (api_probe(GLOBAL_INDEXED_READ_API_SOURCE, source, report, diagnostics, route) can Global{Read,Write})
    if tamper == 1:
        report.source_annotations.clear()
    elif tamper == 2:
        match report.source_declarations[0]:
            Ast::Decl.Const(name, _, initializer, is_global, position):
                extent_position: Ast::Pos = position
                wider_type: Ast::Expr = Ast::Expr.Index(Ast::Expr.Ident("i64", extent_position), Ast::Expr.IntLit(2, extent_position), extent_position)
                report.source_declarations[0] <- Ast::Decl.Const(name, wider_type, initializer, is_global, position)
            _:
                pass
        for index in 0..<report.traces.records.count |index, report|:
            original: ProofFactTrace = report.traces.records[index]
            if original.kind == "global-mutable-array-type":
                report.traces.records[index] <- ProofFactTrace{expression: original.expression, kernel_expression: original.kernel_expression, kind: "type-bound", line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
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

def api_refinement_precondition_mutation_probe(source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&) -> bool can Memory.Allocate, Abort.Panic:
    (api_probe(REFINEMENT_API_SOURCE, source, report, diagnostics, 1) can Global{Read,Write})
    return false if report.failed != 0 or report.replay_gaps != 0
    alias_changed: mutable bool = false
    for index in 0..<report.source_declarations.count |index, report, alias_changed|:
        match report.source_declarations[index]:
            Ast::Decl.Alias(name, target, position):
                match target:
                    Ast::Expr.Refinement(base, _, refinement_position):
                        forged_predicate: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("self", refinement_position), TokenKind.Lt, Ast::Expr.IntLit(0, refinement_position), refinement_position)
                        report.source_declarations[index] <- Ast::Decl.Alias(name, Ast::Expr.Refinement(base, forged_predicate, refinement_position), position)
                        alias_changed <- true
                    _:
                        pass
            _:
                pass
    return false if not alias_changed
    (proof_replay_certificates(report) can Global{Read,Write})
    return report.replay_gaps > 0

def main() -> i64 can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    diagnostics: mutable darray[Semantic::Diagnostic] = []
    for route in 0..<3 |route, source, report, diagnostics|:
        if route < 2:
            (api_probe_before_replay(SOURCE_ASSERT_BY_POSITIVE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
            return 247 if report.failed != 0 or report.findings.count != 0 or report.replayed != 0
            (proof_replay_certificates(&report) can Global{Read,Write})
            return 248 if report.replay_gaps != 0 or not proof_report_source_admission_invariants_consistent(report)
            (api_probe_before_replay(SOURCE_ASSERT_BY_NESTED_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
            return 249 if not any finding in report.findings where finding.kind == "source-obligation-inventory" and finding.status == "unsupported"
            return 250 if report.replayed != 0
            (proof_replay_certificates(&report) can Global{Read,Write})
            return 251 if proof_report_source_admission_invariants_consistent(report)
        for index in 0..<19 |index, route, source, report, diagnostics|:
            (api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
            return 170 if report.certificates.count == 0 or report.proven == 0
            (api_probe(INVALID_API_SOURCES[index], &source, &report, &diagnostics, route) can Global{Read,Write})
            return 171 if report.certificates.count != 0 or report.goal_attempts.count != 0 or report.proven != 0
            return 172 if report.source_declarations.count != 0 or report.traces.records.count != 0 or report.kernel.nodes.count != 0
            expected_kind: sview = "semantic-source-inadmissible" if index < 3 or index >= 7 else "arithmetic-safety-refuted"
            return 173 if not any finding in report.findings where finding.kind == expected_kind
            if route != 0 and (index < 3 or index >= 7):
                return 174 if not any diagnostic in diagnostics where Semantic::diagnostic_severity(diagnostic) == 1
            if route != 0 and index >= 7:
                grant_index: usize = index - 7
                expected_global_effect: sview = INVALID_GLOBAL_GRANT_EXPECTED_EFFECTS[grant_index]
                expected_global_actual: sview = INVALID_GLOBAL_GRANT_EXPECTED_GLOBALS[grant_index]
                return 199 if not any diagnostic in diagnostics where diagnostic.expected == expected_global_effect and diagnostic.actual == expected_global_actual and Semantic::diagnostic_severity(diagnostic) == 1
        (api_probe(GLOBAL_READ_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 194 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(GLOBAL_WRITE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 195 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(GLOBAL_QUALIFIED_READ_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 214 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0 or (route != 0 and any diagnostic in diagnostics where Semantic::diagnostic_severity(diagnostic) == 1)
        (api_probe(GLOBAL_QUALIFIED_WRITE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 215 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0 or (route != 0 and any diagnostic in diagnostics where Semantic::diagnostic_severity(diagnostic) == 1)
        (api_probe(GLOBAL_INDEXED_READ_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 196 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        for tamper in 1..<3 |tamper, source, report, diagnostics, route|:
            (api_global_array_replay_probe(&source, &report, &diagnostics, route, tamper) can Global{Read,Write})
            return 213 if report.replay_gaps == 0
        (api_probe(GLOBAL_INDEXED_WRITE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 197 if report.failed != 0 or report.proven != report.obligations or report.replay_gaps != 0 or report.findings.count != 0
        (api_probe(GLOBAL_MUTABLE_REFERENCE_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        # The source grant is correct on all API routes; the proof checker currently refuses the
        # independent global-borrow lifetime obligation as unsupported.
        return 198 if report.replay_gaps != 0 or (route != 0 and any diagnostic in diagnostics where Semantic::diagnostic_severity(diagnostic) == 1)
        (api_probe(GLOBAL_MUTABLE_INDEX_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        if route == 0:
            return 211 if report.source_declarations.count == 0
        else:
            return 211 if any diagnostic in diagnostics where Semantic::diagnostic_severity(diagnostic) == 1
        return 212 if report.replay_gaps != 0
        (api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 175 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
        (api_probe(REFINEMENT_API_SOURCE, &source, &report, &diagnostics, route) can Global{Read,Write})
        return 190 if report.certificates.count == 0
        return 191 if report.proven == 0
        if route == 2:
            # The focused API currently proves and replays the refinement theorem but its
            # source-inventory adapter conservatively refuses this signature-derived ensure.
            return 192 if report.replay_gaps != 0 or report.findings.count != 1 or report.findings[0].kind != "source-obligation-inventory"
        else:
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
    return 218 if not (api_refinement_precondition_mutation_probe(&source, &report, &diagnostics) can Global{Read,Write})
    (api_probe(PARAMETER_TYPE_BOUND_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    genuine_type_bound: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, genuine_type_bound|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 1:
            genuine_type_bound <- index
            break
    return 219 if genuine_type_bound >= report.traces.records.count
    return 220 if not (proof_replay_fact_trace_entry(&report, genuine_type_bound) can Global{Read,Write})
    forged_position: Ast::Pos = Ast::pos_at_line(1)
    forged_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("value", forged_position), TokenKind.Lt, Ast::Expr.Ident("value", forged_position), forged_position)
    forged_encoding: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_expression, &report, "checked")
    return 221 if not forged_encoding.known
    report.traces.records.push(ProofFactTrace{expression: forged_expression, kernel_expression: forged_encoding.root, kind: "type-bound", line: 1, name: "checked", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0})
    return 222 if (proof_replay_fact_trace_entry(&report, report.traces.records.count - 1) can Global{Read,Write})
    cast_arguments: darray[Ast::Expr] = []
    cast_names: darray[sview] = []
    cast_call: Ast::Expr = Ast::Expr.Call(Ast::Expr.Field(Ast::Expr.Ident("value", forged_position), "i32", forged_position), cast_arguments, cast_names, forged_position)
    forged_cast: Ast::Expr = Ast::Expr.Binary(cast_call, TokenKind.EqEq, Ast::Expr.Ident("value", forged_position), forged_position)
    forged_cast_encoding: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_cast, &report, "checked")
    return 223 if not forged_cast_encoding.known
    report.traces.records.push(ProofFactTrace{expression: forged_cast, kernel_expression: forged_cast_encoding.root, kind: "type-bound", line: 1, name: "checked", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0})
    return 224 if (proof_replay_fact_trace_entry(&report, report.traces.records.count - 1) can Global{Read,Write})
    (api_probe(COUNTING_LOOP_TYPE_BOUND_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    genuine_loop_type_bound: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, genuine_loop_type_bound|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 2:
            genuine_loop_type_bound <- index
            break
    return 225 if genuine_loop_type_bound >= report.traces.records.count
    return 226 if not (proof_replay_fact_trace_entry(&report, genuine_loop_type_bound) can Global{Read,Write})
    (api_probe(COUNTING_LOOP_TYPE_BOUND_SCOPE_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    loop_scope_trace_index: mutable usize = report.traces.records.count
    inside_loop_certificate: mutable usize = report.certificates.count
    outside_loop_certificate: mutable usize = report.certificates.count
    for index in 0..<report.traces.records.count |index, report, loop_scope_trace_index|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 2:
            loop_scope_trace_index <- index
            break
    for index in 0..<report.certificates.count |index, report, inside_loop_certificate, outside_loop_certificate|:
        certificate: ProofGoalCertificate = report.certificates[index]
        if certificate.name == "checked" and certificate.line == 4:
            inside_loop_certificate <- index
        if certificate.name == "checked" and certificate.line == 6:
            outside_loop_certificate <- index
    return 239 if loop_scope_trace_index >= report.traces.records.count or inside_loop_certificate >= report.certificates.count or outside_loop_certificate >= report.certificates.count
    loop_scope_trace: ProofFactTrace = report.traces.records[loop_scope_trace_index]
    report.trace_owner_line <- report.certificates[inside_loop_certificate].line
    report.trace_consumer_certificate_index <- inside_loop_certificate + 1
    return 240 if not proof_replay_type_bound_source_valid(report, loop_scope_trace)
    report.trace_owner_line <- report.certificates[outside_loop_certificate].line
    report.trace_consumer_certificate_index <- outside_loop_certificate + 1
    return 241 if proof_replay_type_bound_source_valid(report, loop_scope_trace)
    forged_outside_attempt_index: mutable usize = report.goal_attempts.count
    for index in 0..<report.goal_attempts.count |index, report, forged_outside_attempt_index, outside_loop_certificate|:
        attempt: ProofGoalAttempt = report.goal_attempts[index]
        if attempt.has_certificate and attempt.certificate_index == outside_loop_certificate:
            forged_outside_attempt_index <- index
            break
    return 242 if forged_outside_attempt_index >= report.goal_attempts.count
    saved_outside_attempt: ProofGoalAttempt = report.goal_attempts[forged_outside_attempt_index]
    saved_outside_certificate: ProofGoalCertificate = report.certificates[outside_loop_certificate]
    report.goal_attempts[forged_outside_attempt_index] <- ProofGoalAttempt{goal: saved_outside_attempt.goal, budget_exhausted: saved_outside_attempt.budget_exhausted, facts_start: saved_outside_attempt.facts_start, facts_count: saved_outside_attempt.facts_count, kernel_goal: saved_outside_attempt.kernel_goal, kernel_facts_start: saved_outside_attempt.kernel_facts_start, kernel_facts_count: saved_outside_attempt.kernel_facts_count, line: report.certificates[inside_loop_certificate].line, name: saved_outside_attempt.name, rule: saved_outside_attempt.rule, proven: saved_outside_attempt.proven, has_certificate: saved_outside_attempt.has_certificate, certificate_index: saved_outside_attempt.certificate_index}
    report.certificates[outside_loop_certificate] <- ProofGoalCertificate{goal: saved_outside_certificate.goal, facts_start: saved_outside_certificate.facts_start, facts_count: saved_outside_certificate.facts_count, kernel_goal: saved_outside_certificate.kernel_goal, kernel_facts_start: saved_outside_certificate.kernel_facts_start, kernel_facts_count: saved_outside_certificate.kernel_facts_count, line: report.certificates[inside_loop_certificate].line, name: saved_outside_certificate.name, rule: saved_outside_certificate.rule, replayed: saved_outside_certificate.replayed}
    report.trace_owner_line <- report.certificates[inside_loop_certificate].line
    report.trace_consumer_certificate_index <- outside_loop_certificate + 1
    return 243 if proof_replay_type_bound_source_valid(report, loop_scope_trace)
    report.goal_attempts[forged_outside_attempt_index] <- saved_outside_attempt
    report.certificates[outside_loop_certificate] <- saved_outside_certificate
    report.trace_owner_line <- 0
    report.trace_consumer_certificate_index <- 0
    (api_probe(LOOP_REBIND_TYPE_BOUND_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    return 244 if report.failed != 0 or report.replay_gaps != 0 or report.certificates.count == 0
    for certificate in report.certificates:
        return 245 if not certificate.replayed
    (api_probe(FIXED_ARRAY_TYPE_BOUND_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    genuine_array_type_bound: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, genuine_array_type_bound|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 3:
            genuine_array_type_bound <- index
            break
    return 227 if genuine_array_type_bound >= report.traces.records.count
    return 228 if not (proof_replay_fact_trace_entry(&report, genuine_array_type_bound) can Global{Read,Write})
    (api_probe(LOCAL_FIXED_ARRAY_TYPE_BOUND_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    local_array_type_bound_count: mutable usize = 0
    for index in 0..<report.traces.records.count |index, report, local_array_type_bound_count|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 3:
            local_array_type_bound_count <- local_array_type_bound_count + 1
            return 229 if not (proof_replay_fact_trace_entry(&report, index) can Global{Read,Write})
    return 230 if local_array_type_bound_count == 0
    local_extent_position: Ast::Pos = Ast::pos_at_line(3)
    local_count: Ast::Expr = Ast::Expr.Field(Ast::Expr.Ident("values", local_extent_position), "count", local_extent_position)
    forged_local_extent: Ast::Expr = Ast::Expr.Binary(local_count, TokenKind.EqEq, Ast::Expr.IntLit(2, local_extent_position), local_extent_position)
    forged_local_extent_encoding: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_local_extent, &report, "checked")
    return 231 if not forged_local_extent_encoding.known
    report.traces.records.push(ProofFactTrace{expression: forged_local_extent, kernel_expression: forged_local_extent_encoding.root, kind: "type-bound", line: 3, name: "checked", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0})
    return 232 if (proof_replay_fact_trace_entry(&report, report.traces.records.count - 1) can Global{Read,Write})
    (api_probe(LOCAL_SCALAR_TYPE_BOUND_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    local_scalar_type_bounds: mutable usize = 0
    for index in 0..<report.traces.records.count |index, report, local_scalar_type_bounds|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 3:
            local_scalar_type_bounds <- local_scalar_type_bounds + 1
            return 235 if not (proof_replay_fact_trace_entry(&report, index) can Global{Read,Write})
    return 236 if local_scalar_type_bounds == 0
    wrong_local_width_position: Ast::Pos = Ast::pos_at_line(3)
    wrong_local_width_arguments: darray[Ast::Expr] = [Ast::Expr.Ident("status", wrong_local_width_position), Ast::Expr.IntLit(64, wrong_local_width_position)]
    wrong_local_width_names: darray[sview] = []
    wrong_local_width: Ast::Expr = Ast::Expr.Call(Ast::Expr.Ident("__elisa_unsigned_type_bound", wrong_local_width_position), wrong_local_width_arguments, wrong_local_width_names, wrong_local_width_position)
    wrong_local_width_encoding: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(wrong_local_width, &report, "checked")
    return 237 if not wrong_local_width_encoding.known
    report.traces.records.push(ProofFactTrace{expression: wrong_local_width, kernel_expression: wrong_local_width_encoding.root, kind: "type-bound", line: 3, name: "checked", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0})
    return 238 if (proof_replay_fact_trace_entry(&report, report.traces.records.count - 1) can Global{Read,Write})
    (api_probe(FIXED_ARRAY_NO_BOUND_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    missing_bound_position: Ast::Pos = Ast::pos_at_line(2)
    missing_bound: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("index", missing_bound_position), TokenKind.Lt, Ast::Expr.Field(Ast::Expr.Ident("values", missing_bound_position), "count", missing_bound_position), missing_bound_position)
    missing_bound_encoding: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(missing_bound, &report, "checked")
    return 233 if not missing_bound_encoding.known
    report.traces.records.push(ProofFactTrace{expression: missing_bound, kernel_expression: missing_bound_encoding.root, kind: "type-bound", line: 2, name: "checked", dependency: "", premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: 0})
    return 234 if (proof_replay_fact_trace_entry(&report, report.traces.records.count - 1) can Global{Read,Write})
    (api_probe(DYNAMIC_ARRAY_GUARD_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    return 239 if report.failed != 0 or report.replay_gaps != 0
    dynamic_bound_index: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, dynamic_bound_index|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 5:
            match trace.expression:
                Ast::Expr.Binary(Ast::Expr.Ident("index", _), TokenKind.Lt, Ast::Expr.Field(Ast::Expr.Ident("values", _), "count", _), _):
                    dynamic_bound_index <- index
                _:
                    pass
    return 240 if dynamic_bound_index >= report.traces.records.count
    dynamic_bound_trace: ProofFactTrace = report.traces.records[dynamic_bound_index]
    return 241 if not (proof_replay_fact_trace_entry(&report, dynamic_bound_index) can Global{Read,Write})
    nearby_position: Ast::Pos = Ast::pos_at_line(5)
    nearby_count: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Field(Ast::Expr.Ident("values", nearby_position), "count", nearby_position), TokenKind.Minus, Ast::Expr.IntLit(1, nearby_position), nearby_position)
    nearby_bound: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("index", nearby_position), TokenKind.Lt, nearby_count, nearby_position)
    nearby_trace: ProofFactTrace = ProofFactTrace{expression: nearby_bound, kernel_expression: dynamic_bound_trace.kernel_expression, kind: "type-bound", line: dynamic_bound_trace.line, name: dynamic_bound_trace.name, dependency: dynamic_bound_trace.dependency, premises_start: dynamic_bound_trace.premises_start, premises_count: dynamic_bound_trace.premises_count, kernel_premises_start: dynamic_bound_trace.kernel_premises_start, kernel_premises_count: dynamic_bound_trace.kernel_premises_count, summary_bindings_start: dynamic_bound_trace.summary_bindings_start, summary_bindings_count: dynamic_bound_trace.summary_bindings_count, summary_requires_start: dynamic_bound_trace.summary_requires_start, summary_requires_count: dynamic_bound_trace.summary_requires_count, summary_ensure_index: dynamic_bound_trace.summary_ensure_index, owner_line: dynamic_bound_trace.owner_line}
    return 242 if (proof_replay_type_bound_source_valid(report, nearby_trace) can Global{Read,Write})
    unrelated_bound: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("index", nearby_position), TokenKind.Lt, Ast::Expr.Field(Ast::Expr.Ident("other", nearby_position), "count", nearby_position), nearby_position)
    unrelated_trace: ProofFactTrace = ProofFactTrace{expression: unrelated_bound, kernel_expression: dynamic_bound_trace.kernel_expression, kind: "type-bound", line: dynamic_bound_trace.line, name: dynamic_bound_trace.name, dependency: dynamic_bound_trace.dependency, premises_start: dynamic_bound_trace.premises_start, premises_count: dynamic_bound_trace.premises_count, kernel_premises_start: dynamic_bound_trace.kernel_premises_start, kernel_premises_count: dynamic_bound_trace.kernel_premises_count, summary_bindings_start: dynamic_bound_trace.summary_bindings_start, summary_bindings_count: dynamic_bound_trace.summary_bindings_count, summary_requires_start: dynamic_bound_trace.summary_requires_start, summary_requires_count: dynamic_bound_trace.summary_requires_count, summary_ensure_index: dynamic_bound_trace.summary_ensure_index, owner_line: dynamic_bound_trace.owner_line}
    return 243 if (proof_replay_type_bound_source_valid(report, unrelated_trace) can Global{Read,Write})
    (api_probe(DYNAMIC_ARRAY_SHADOWED_GUARD_API_SOURCE, &source, &report, &diagnostics, 1) can Global{Read,Write})
    shadowed_position: Ast::Pos = Ast::pos_at_line(6)
    shadowed_bound: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("index", shadowed_position), TokenKind.Lt, Ast::Expr.Field(Ast::Expr.Ident("values", shadowed_position), "count", shadowed_position), shadowed_position)
    shadowed_encoding: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(shadowed_bound, &report, "checked")
    return 244 if not shadowed_encoding.known
    shadowed_trace: ProofFactTrace = ProofFactTrace{expression: shadowed_bound, kernel_expression: shadowed_encoding.root, kind: "type-bound", line: 6, name: dynamic_bound_trace.name, dependency: dynamic_bound_trace.dependency, premises_start: 0, premises_count: 0, kernel_premises_start: 0, kernel_premises_count: 0, summary_bindings_start: 0, summary_bindings_count: 0, summary_requires_start: 0, summary_requires_count: 0, summary_ensure_index: 0, owner_line: dynamic_bound_trace.owner_line}
    return 245 if (proof_replay_type_bound_source_valid(report, shadowed_trace) can Global{Read,Write})
    return 246 if report.replay_gaps != 0
    return 0
'''
ast_nodes = (ROOT / "build/snapshot/Elisa-compiler/src/parser/ast_nodes.elisa").read_text()
statement_nodes = ast_nodes.split("    enum Stmt is Node:", 1)[1].split("    enum Decl is Node:", 1)[0]
statement_variants = set(re.findall(r"^        ([A-Z][A-Za-z0-9_]*)\b", statement_nodes, re.MULTILINE))
type_bound_source = (ROOT / "src/proof/replay/type_bound_loop_scope.elisa").read_text()
consumer_visitor = type_bound_source.split("def proof_replay_type_bound_consumer_source_site_in_body(", 1)[1].split("def proof_replay_type_bound_loop_consumer_in_scope(", 1)[0]
visited_statement_variants = set(re.findall(r"Ast::Stmt\.([A-Z][A-Za-z0-9_]*)", consumer_visitor))
unvisited_statement_variants = sorted(statement_variants - visited_statement_variants)
if unvisited_statement_variants:
    raise AssertionError(f"type-bound consumer scope visitor misses pinned AST statement variants: {unvisited_statement_variants}")
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Direct API semantic admission: source-goal and assert-by identity, loop-binder scope, Global grants, source-bound refinements, and reused-state clearing pass")
