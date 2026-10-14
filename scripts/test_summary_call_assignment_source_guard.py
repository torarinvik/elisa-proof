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

print("summary call source guard: assignment forms and cached exact-owner indexing are preserved")
