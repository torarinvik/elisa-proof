"""Keep root-key candidate buckets selective without dropping exact matches."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/model/report_goal_fact_index.elisa").read_text(encoding="utf-8")
recording_source = (ROOT / "src/proof/model/report_recording.elisa").read_text(encoding="utf-8")
candidate = source.split("def proof_goal_fact_index_trace_root_possible(", 1)[1].split(
    "def proof_goal_fact_index_match_trace(", 1
)[0]
assert "root_tag_heads.count != PROOF_GOAL_FACT_ROOT_TAG_COUNT" in candidate
assert "return (true, unmatched > 0) if root_tag == 0" in candidate
assert "proof_goal_fact_root_key_hash(root_result.root, &work)" in candidate
assert "root_key_slot_heads[slot]" in candidate
assert "proof_trace_root_may_equal(root_result.root, fact_roots[fact_index])" in candidate
assert "proof_kernel_ast_support_charge_with_work(1, &work)" in candidate
scan = source.split("def proof_goal_fact_index_scan(", 1)[1]
assert "root_tag_heads[0]" in scan
root_key = source.split("def proof_goal_fact_root_key_hash(", 1)[1].split(
    "def proof_goal_fact_index_build(", 1
)[0]
assert "proof_expr_shape_mix(ElisaProofKernelCore::PROOF_KERNEL_FNV1A_OFFSET_BASIS.u32(), tag.i64())" in root_key
assert "proof_expr_shape_operator_code(operator).i64()" in root_key
assert "proof_name_hash(name).i64()" in root_key

matcher = source.split("def proof_goal_fact_index_match_trace(", 1)[1].split(
    "def proof_goal_fact_index_scan(", 1
)[0]
assert "shape_hash: u32" in matcher
assert "proof_goal_trace_shape_hash" not in matcher

root_tags = recording_source.split("def proof_trace_root_tag(", 1)[1]
root_tag_body = root_tags.split("def proof_certificate_fact_is_traced(", 1)[0]
tag_rows = re.findall(r"Ast::Expr\.([A-Za-z0-9_]+)(?:\([^\n]*\))?:\s*\n\s*return ([0-9]+)", root_tag_body)
assert len(tag_rows) >= 31
assert len({tag for _, tag in tag_rows}) == len(tag_rows)
assert len({constructor for constructor, _ in tag_rows}) == len(tag_rows)
for constructor in (
    "Ast::Expr.Absent",
    "Ast::Expr.FloatLit",
    "Ast::Expr.StringLit",
    "Ast::Expr.CharLit",
    "Ast::Expr.Block",
    "Ast::Expr.Match",
    "Ast::Expr.Catch",
    "Ast::Expr.Comprehension",
    "Ast::Expr.Refinement",
    "Ast::Expr.GetElse",
    "Ast::Expr.Lambda",
    "Ast::Expr.Scope",
    "Ast::Expr.ShorthandMember",
    "Ast::Expr.Slice",
    "Ast::Expr.IndexN",
    "Ast::Expr.Move",
    "Ast::Expr.RegionNew",
    "Ast::Expr.Array",
    "Ast::Expr.Tuple",
    "Ast::Expr.SetLit",
    "Ast::Expr.DictLit",
    "Ast::Expr.Construct",
    "Ast::Expr.RecordUpdate",
    "Ast::Expr.If",
):
    assert constructor in root_tags, constructor

print("goal fact index reuses bounded shape hashes and conservatively includes unknown roots")
