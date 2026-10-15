"""Pin the bounded policy for calls nested in parameter defaults."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMISSION = (ROOT / "src/proof/model/report_default_call_requires_admission.elisa").read_text(encoding="utf-8")
CALL_REQUIRES = (ROOT / "src/proof/model/report_call_requires_resolution.elisa").read_text(encoding="utf-8")
INVARIANTS = (ROOT / "src/proof/model/report_invariants.elisa").read_text(encoding="utf-8")
STRUCTURE = (ROOT / "src/proof/model/report_structure_bound_failure.elisa").read_text(encoding="utf-8")


def body(source: str, name: str) -> str:
    marker = f"def {name}("
    start = source.index(marker)
    following = source.find("\n        def ", start + len(marker))
    return source[start:] if following < 0 else source[start:following]


entry = body(ADMISSION, "proof_report_default_call_requires_safe")
assert "signature_lines.count != signature_kinds.count" in entry
assert "signature_lines.count != signature_exprs.count" in entry
assert "proof_report_default_call_requires_declarations" in entry

defaults = body(ADMISSION, "proof_report_default_call_requires_declarations")
assert "parameter.has_default" in defaults
assert "parameter.default_value" in defaults
assert "proof_replay_summary_expr_cost(parameter.default_value" in defaults
assert "proof_report_call_requires_collect_runtime_expression(parameter.default_value" in defaults
assert "argument_names.count != 0" in defaults
assert 'qualifiers[row] != ""' in defaults
assert "for earlier_index in 0..<parameter_index" in defaults
assert "earlier_name == callee_name" in defaults
assert "proof_report_default_call_requires_has_scoped_binders(parameter.default_value" in defaults
assert "proof_report_default_call_requires_target_safe" in defaults
assert "return false" in defaults  # Unsupported/opaque call shapes fail closed.

target = body(ADMISSION, "proof_report_default_call_requires_unique_target")
assert "parameters.count == argument_count and not nested_scope" in target
assert "parameter.has_default" in target
assert 'kind == "requires"' in target
assert 'signature_kinds[row] == "requires"' in target
assert "matched == 1 and safe" in target

# The selected-call resolver does not include defaults in its producer event matching;
# the new admission helper must remain a separate source-bound refusal until that protocol
# gains a stable default-site plus outer-invocation identity.
selected = body(CALL_REQUIRES, "proof_report_call_requires_selected_source_match")
assert "caller_parameters" in selected
assert "parameter.has_default" in selected  # Callee default arguments remain outside this event protocol.
assert "proof_report_call_requires_collect_runtime_calls(caller_body" in selected

# The refusal must run at parser-backed source admission, after report mirrors are
# checked and before the checked view receives a positive source-bound receipt.
assert 'include "./report_default_call_requires_admission.elisa"' in INVARIANTS
assert "proof_report_default_call_requires_safe(source.file.top_decls" in STRUCTURE
assert '"source-default-call-requires-unsupported"' in STRUCTURE
assert '"source-admission-work-limit" if source_work > source_work_limit' in STRUCTURE

scoped_binders = body(ADMISSION, "proof_report_default_call_requires_has_scoped_binders")
for scope in (
    "Ast::Expr.Comprehension",
    "Ast::Expr.Catch",
    "Ast::Expr.GetElse",
    "Ast::Expr.Block",
    "Ast::Expr.Lambda",
):
    assert scope in scoped_binders
assert "depth >= PROOF_REPORT_DEFAULT_CALL_REQUIRES_DEPTH_LIMIT" in scoped_binders
assert "not proof_report_source_work_charge(1, work)" in scoped_binders

print("default call-requires admission: requiring or unresolved default calls fail closed")
