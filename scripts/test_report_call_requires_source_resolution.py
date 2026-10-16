"""Keep tagged call-precondition evidence tied to a real parser-origin call site."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVARIANTS = (ROOT / "src/proof/model/report_invariants.elisa").read_text(encoding="utf-8")
RESOLUTION = (ROOT / "src/proof/model/report_call_requires_resolution.elisa").read_text(encoding="utf-8")
LEDGER = (ROOT / "src/proof/model/obligation_entry.elisa").read_text(encoding="utf-8")
SOURCE_BOUNDARY = (ROOT / "src/proof/model/report_structure_bound_failure.elisa").read_text(encoding="utf-8")


def body(source: str, name: str) -> str:
    marker = f"def {name}("
    start = source.index(marker)
    following = source.find("\n        def ", start + len(marker))
    return source[start:] if following < 0 else source[start:following]


invariant = body(INVARIANTS, "proof_report_proven_attempts_consistent_with_declarations")
assert "source_site: (complete: bool, found: bool) = proof_report_call_requires_source_index_contains" in invariant
assert "not source_site.complete or not source_site.found" in invariant
assert invariant.index("not source_site.complete or not source_site.found") < invariant.index(
    "proof_report_call_requires_selected_source_match(declarations, report, attempt, attempt_index, source_work)"
)
assert "proof_report_call_requires_source_index_build(declarations, source_work)" in invariant

report_only_wrapper = body(INVARIANTS, "proof_report_proven_attempts_consistent")
assert "report.source.source_declarations" in report_only_wrapper

assert "proof_report_proven_attempts_consistent_with_declarations(report, source.file.top_decls, source_work)" in SOURCE_BOUNDARY

resolver = body(RESOLUTION, "proof_report_call_requires_selected_source_match")
assert "declarations: darray[Ast::Decl]&" in resolver
assert "report.source.source_declarations" not in resolver
assert "proof_report_call_requires_collect_runtime_calls(caller_body" in resolver
assert "proof_report_call_requires_position_equal(call_position, attempt.source_call_position)" in resolver
assert "proof_report_call_requires_selected_source_match(declarations, report, attempt, attempt_index, source_work)" in invariant
assert "tagged_for_call % requirements.count != 0" in resolver
assert "Ast::Decl.Extern(_, _, _, _, _, _, _, position)" in resolver
assert "same_line_declarations <- same_line_declarations + 1 if position.line == attempt.owner_function_line" in resolver
assert "clause_counts[requires_index] != visits" in resolver
assert "failed_tag_count" not in resolver

ledger_match = body(RESOLUTION, "proof_report_call_requires_ledger_match")
assert "attempt_index: usize" in ledger_match
assert "attempt_index < entry.attempts_start or attempt_index >= event_end" in ledger_match
assert "contains_attempt and selected_in_event == 1" in ledger_match

runtime_calls = body(RESOLUTION, "proof_report_call_requires_collect_runtime_calls")
assert "Ast::Stmt.Contract(kind, expression, _):" in runtime_calls
assert "sview_len(kind)" in runtime_calls
assert "if kind == \"assert\"" in runtime_calls
assert 'elif kind != "requires" and not proof_is_ensure_kind(kind)' in runtime_calls
assert '"invariant", "decreases", "decreases*", "changes", "preserves"' in runtime_calls
assert 'if block_kind != "assert_by"' in runtime_calls
assert 'Ast::Stmt.Contract("assert", goal, _)' in runtime_calls
assert "return false if nested.count == 0" in runtime_calls
assert "_:\n                        return false" in runtime_calls
assert "parameter.default_value" not in runtime_calls

# Return-value matches and catches use a specialized walker. Their arm guards can
# execute calls too, so keep those traversals pinned alongside the generic walker.
runtime_return = body(RESOLUTION, "proof_report_call_requires_collect_runtime_return")
assert "Ast::Expr.Match(scrutinee, arms, _)" in runtime_return
assert "Ast::Expr.Catch(guarded, arms, _)" in runtime_return
assert runtime_return.count("proof_report_call_requires_collect_runtime_expression(arm.guard") == 2

same_site = body(RESOLUTION, "proof_report_call_requires_same_site")
assert same_site.index("sview_len(candidate.name)") < same_site.index("candidate.name != attempt.name")
assert same_site.index("sview_len(candidate.source_call_callee_name)") < same_site.index(
    "candidate.source_call_callee_name != attempt.source_call_callee_name"
)
assert same_site.index("sview_len(candidate.source_call_callee_module)") < same_site.index(
    "candidate.source_call_callee_module != attempt.source_call_callee_module"
)

for field in (
    "source_call_position: mutable Ast::Pos",
    "source_call_callee_name: mutable sview",
    "source_call_callee_module: mutable sview",
    "source_call_callee_line: mutable u32",
    "source_call_callee_offset: mutable u32",
    "source_call_requires_index: mutable usize",
):
    assert field in LEDGER

ledger_check = body(INVARIANTS, "proof_report_source_postcondition_inventory_consistent_with_work")
assert 'obligation.source_kind == "call-requires"' in ledger_check
assert "obligation.attempts_start > report.results.goal_attempts.count" in ledger_check
assert "selected_call_attempts != 1" in ledger_check
assert "obligation.proven or obligation.attempts_count != 0" in ledger_check
attempt_ledger = body(INVARIANTS, "proof_report_goal_attempts_bounded_by_obligations")
assert '(event.proven and event.attempts_count == 0 and event.source_kind != "frame-clause")' in attempt_ledger
assert 'event.source_kind == "frame" and event.attempts_count > 0' in attempt_ledger
for field in (
    "attempt.source_call_position",
    "attempt.source_call_callee_name",
    "attempt.source_call_callee_module",
    "attempt.source_call_callee_line",
    "attempt.source_call_callee_offset",
    "attempt.source_call_requires_index",
):
    assert field in ledger_check

admission = body(INVARIANTS, "proof_report_source_admission_failure")
assert "proof_report_source_postcondition_inventory_consistent_with_work(report, &source_work)" in admission
assert 'return "postcondition-inventory" if not postconditions_consistent' in admission

postcondition_inventory = body(INVARIANTS, "proof_report_source_postcondition_inventory_consistent_with_work")
assert "proof_report_call_requires_source_census_matches_ledger" not in postcondition_inventory
assert 'include "./report_call_requires_census.elisa"' not in INVARIANTS
assert "proof_report_call_requires_source_census_matches_ledger" not in SOURCE_BOUNDARY
assert "proof_report_proven_attempts_consistent_with_declarations(report, source.file.top_decls, source_work)" in SOURCE_BOUNDARY

ledger_match = body(RESOLUTION, "proof_report_call_requires_ledger_match")
assert ledger_match.index("sview_len(entry.source_call_callee_name)") < ledger_match.index(
    "entry.source_call_callee_name != attempt.source_call_callee_name"
)
assert ledger_match.index("sview_len(entry.source_call_callee_module)") < ledger_match.index(
    "entry.source_call_callee_module != attempt.source_call_callee_module"
)

print("call-requires source resolution: selected attempts must match frozen parser call sites")
