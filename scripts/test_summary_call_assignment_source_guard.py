#!/usr/bin/env python3
"""Keep source call-site discovery aligned with supported plain local rebinding syntax."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/replay/summary_call_sites.elisa").read_text(encoding="utf-8")
same_source = source.split("def proof_replay_summary_call_same_source_statement(", 1)[1].split(
    "def proof_replay_summary_call_same_source_declarations(", 1
)[0]

# Both parser forms are plain local rebinding. Compound assignments intentionally remain
# unsupported; the exact call-span and unique-occurrence checks run after this syntax dispatch.
assert "Ast::Stmt.Assign(_, TokenKind.Assign, value, position)" in same_source
assert "Ast::Stmt.Assign(_, TokenKind.LArrow, value, position)" in same_source
assert "Ast::Stmt.Assign(_, TokenKind.AddAssign" not in same_source

source_site = source.split("def proof_replay_summary_call_same_source_site(", 1)[1].split(
    "def proof_replay_summary_call_arguments_match(", 1
)[0]
assert "proof_replay_deterministic_call_declaration_index_ensure" in source_site
assert "proof_replay_summary_call_same_source_indexed" in source_site
assert "proof_replay_summary_call_same_source_declarations(" not in source_site
indexed_match = source.split("def proof_replay_summary_call_same_source_indexed(", 1)[1].split(
    "def proof_replay_summary_call_owner_body_from_index(", 1
)[0]
assert "proof_replay_deterministic_declaration_group" in indexed_match
assert "entry.name == trace.name" in indexed_match
assert "position.line == owner_line" in indexed_match
owner_lookup = source.split("def proof_replay_summary_call_owner_body_from_index(", 1)[1].split(
    "def proof_replay_summary_call_same_source_site(", 1
)[0]
assert "proof_replay_deterministic_declaration_group" in owner_lookup
assert "matches <- matches + 1" in owner_lookup
assert "matches > 1" in owner_lookup

fixture = (ROOT / "examples/assignment_rhs_state.elisa").read_text(encoding="utf-8")
assert "value <- assignment_add_one(value)" in fixture

# A repeated, textually identical invocation can have different state or resolution. Rebinding
# must therefore use the exact parser call position whenever the assigned expression is a call.
rebinding = (ROOT / "src/proof/check/bound_call_summaries.elisa").read_text(encoding="utf-8")
position_equal = rebinding.split("def proof_bound_call_summary_position_equal(", 1)[1].split(
    "def proof_rebind_call_summaries(", 1
)[0]
for field in ("line", "column", "offset", "end_line", "end_column", "end_offset"):
    assert f"left.{field} == right.{field}" in position_equal
rebind = rebinding.split("def proof_rebind_call_summaries(", 1)[1]
assert "Ast::Expr.Call(_, _, _, source_position)" in rebind
assert "continue if direct_call and not proof_bound_call_summary_position_equal(trace.source_call_position, direct_call_position)" in rebind

print("summary call source guard: assignment forms and cached exact-owner indexing are preserved")
