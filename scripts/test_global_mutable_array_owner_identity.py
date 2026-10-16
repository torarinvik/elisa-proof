"""Require exact declaration identity when replay validates imported global-array facts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/replay/global_mutable_array_validation.elisa").read_text(encoding="utf-8")


def function_body(name: str) -> str:
    start = SOURCE.index(f"def {name}(")
    end = SOURCE.find("\n        def ", start + 1)
    return SOURCE[start:] if end < 0 else SOURCE[start:end]


assert "declaration_offset: usize" in SOURCE
assert "candidate_position.offset.usize() == declaration_offset" in SOURCE
assert "trace.name, trace.owner_line, report.analysis_2.replay_owner_offset" in SOURCE
assert "owner_position.offset.usize() != report.analysis_2.replay_owner_offset" in SOURCE
assert "not report.analysis_2.replay_owner_offset_valid" in SOURCE
bound_precondition = function_body("proof_replay_global_mutable_array_bound_precondition")
assert "proof_source_analysis_operator_mask_from_source(report.source.source_declarations, report.source.source_annotations, source_work)" in bound_precondition
assert "proof_source_expression_has_overloaded_operator_with_work(expression, operator_mask_status.mask, source_work, operator_work_exhausted)" in bound_precondition
array_fact = function_body("proof_replay_global_mutable_array_type_fact_is_valid_with_work")
assert "proof_source_expression_has_overloaded_operator_with_work(trace.expression, operator_mask_status.mask, source_work, operator_work_exhausted)" in array_fact

print("global mutable array replay binds fact owners by exact source offset")
