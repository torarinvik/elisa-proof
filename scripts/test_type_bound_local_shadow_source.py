"""Ensure local type-bound facts use the source binding name for shadow checks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/proof/replay/type_bound_local_availability.elisa"
TEXT = SOURCE.read_text(encoding="utf-8")
BODY = TEXT.split(
    "def proof_replay_type_bound_local_scalar_consumer_available_with_work(", 1
)[1].split(
    "def proof_replay_type_bound_parameter_consumer_binding_available_with_work(", 1
)[0]

assert 'binding_name: mutable sview = ""' in BODY
assert "binding_name <- local_name" in BODY
assert (
    "proof_replay_type_bound_binding_shadowed_before_consumer_with_work("
    "report, body, binding_name, Ast::expr_pos(trace.expression), true, work)"
    in BODY
)

TYPE_VALIDATION = ROOT / "src/proof/replay/type_bound_validation.elisa"
TYPE_TEXT = TYPE_VALIDATION.read_text(encoding="utf-8")
PARAMETER_WALK = TYPE_TEXT.split(
    "def proof_replay_type_bound_parameter_declaration(", 1
)[1].split("def proof_replay_type_bound_counting_loop_fact(", 1)[0]
assert "matched_parameter_name <- parameter.name" in PARAMETER_WALK
assert "proof_replay_source_body_declares_with_work" not in PARAMETER_WALK

ARRAY_VALIDATION = ROOT / "src/proof/replay/type_bound_array_validation.elisa"
ARRAY_TEXT = ARRAY_VALIDATION.read_text(encoding="utf-8")
assert (
    "proof_replay_type_bound_parameter_consumer_binding_available_with_work("
    "report, trace, matched_parameter_name, function_body, work)"
    in ARRAY_TEXT
)
