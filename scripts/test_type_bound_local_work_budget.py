"""Keep paired local expression sizing within one type-bound work budget."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/replay/type_bound_local_facts.elisa").read_text(encoding="utf-8")
helper = source.split("def proof_replay_type_bound_local_expr_equal_with_work(", 1)[1].split(
    "def proof_replay_type_bound_local_type_name_charge(", 1
)[0]

assert "left_cost: mutable usize = 0" in helper
assert "right_cost: mutable usize = 0" in helper
assert "&left_cost, work, PROOF_REPLAY_TYPE_BOUND_SOURCE_USE_WORK_LIMIT" in helper
assert "&right_cost, work + left_cost, PROOF_REPLAY_TYPE_BOUND_SOURCE_USE_WORK_LIMIT" in helper
assert "cost: usize = left_cost + right_cost" in helper
assert "work + cost * 2" in helper
assert "&cost, work + cost" not in helper

generic_lookup = source.split(
    "def proof_replay_type_bound_local_generic_name_count_with_work(", 1
)[1].split("# Reuse the scope-ranked resolver", 1)[0]
assert "owner_offset" in generic_lookup and "owner_offset_valid" in generic_lookup
assert "proof_source_generic_owner_param_present_in_index_with_work" in generic_lookup
local_shape = source.split("def proof_replay_type_bound_local_type_shape(", 1)[1].split(
    "def proof_replay_type_bound_local_unsigned_width(", 1
)[0]
assert "report.analysis_2.replay_owner_offset" in local_shape
assert "report.analysis_2.replay_owner_offset_valid" in local_shape

call_source = (ROOT / "src/proof/replay/type_bound_call_result.elisa").read_text(encoding="utf-8")
generic_walk = call_source.split(
    "def proof_replay_type_bound_call_type_has_generic_with_work(", 1
)[1].split("def proof_replay_type_bound_call_type_shape(", 1)[0]
assert "declaration_offset" in generic_walk and "declaration_offset_valid" in generic_walk
assert "proof_replay_type_bound_local_generic_name_count_with_work(report, name, declaration_line, declaration_offset, declaration_offset_valid, work)" in generic_walk
assert "resolved_line.line, resolved_callee_offset, resolved_callee_exact, work, 0" in call_source
generic_index_source = (ROOT / "src/proof/replay/source_generic_parameter_index.elisa").read_text(encoding="utf-8")
rows_copy = generic_index_source.split(
    "def proof_replay_source_generic_param_rows_copy(", 1
)[1].split("def proof_replay_source_generic_param_line_index_build(", 1)[0]
assert "return proof_source_generic_owner_param_index_build(report, work)" in rows_copy

print("type-bound local equality and generic-name checks use shared work and exact owner identity")
