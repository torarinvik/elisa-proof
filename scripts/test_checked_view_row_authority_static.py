"""Guard the binding between checked-view rows and receipt verdicts."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "src/proof/model/checked_view_rows.elisa"
VIEW = ROOT / "src/proof/model/checked_view.elisa"
VIEW_ATTEMPTS = ROOT / "src/proof/model/checked_view_attempt_diagnostic.elisa"
RECEIPT = ROOT / "src/proof/model/replay_receipt.elisa"


def body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            result = [line]
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                result.append(following)
            return "\n".join(result)
    raise AssertionError(name)


def struct_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for start, line in enumerate(lines):
        if re.match(rf"\s*struct {re.escape(name)}(?:\[|:)", line):
            indent = len(line) - len(line.lstrip())
            end = start + 1
            while end < len(lines):
                current = lines[end]
                if current.strip() and len(current) - len(current.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[start:end])
    raise AssertionError(f"struct {name} not found in {path}")


def struct_fields(path: Path, name: str) -> list[str]:
    declaration = struct_body(path, name)
    return re.findall(r"^\s{12}([A-Za-z_]\w*):", declaration, re.M)


attempt = body(ROWS, "proof_checked_view_attempt_row_matches_with_work")
assert all(field in attempt for field in ("actual.goal", "actual.facts_start", "actual.kernel_goal", "actual.name", "actual.rule", "actual.source_phase", "actual.float_mode", "actual.source_call_position", "actual.source_call_requires_index", "actual.source_call_callee_name", "actual.loop_transfer_position", "actual.producer_proven", "actual.has_certificate", "actual.certificate_index", "actual.owner_function_line", "actual.owner_function_offset"))
assert "proof_replay_summary_expr_equal_with_work(actual.goal, expected.goal, source_work)" in attempt
for field in struct_fields(ROOT / "src/proof/model.elisa", "ProofGoalAttempt"):
    assert f"actual.{field}" in attempt, field
    assert f"expected.{field}" in attempt, field
theorem = body(ROWS, "proof_checked_view_theorem_row_matches_with_work")
assert all(field in theorem for field in ("actual.name", "actual.line", "actual.proof_goals_start", "actual.recursive", "actual.verified", "actual.verification_reason", "actual.source_offset"))
for field in struct_fields(ROOT / "src/proof/model.elisa", "ProofTheoremSummary"):
    assert f"actual.{field}" in theorem, field
    assert f"expected.{field}" in theorem, field
assert all(field in theorem for field in ("view.theorem_proof_goal_ids.count", "report_goal_ids.count", "theorem_proof_goal_ids[start + offset]", "report_goal_ids[start + offset]", "proof_checked_view_row_charge(1, source_work)"))
creation = body(ROWS, "proof_checked_view_create")
assert all(fragment in creation for fragment in ("theorem_goal_id_count", "theorem_goal_id_count > snapshot_limit - attempt_count - theorem_count", "for goal_id in report.analysis_1.theorems.proof_goal_ids", "theorem_proof_goal_ids: theorem_proof_goal_ids"))
rows = body(ROWS, "proof_checked_view_rows_match")
assert "proof_checked_view_rows_match_with_work(view, &source_work)" in rows
rows_with_work = body(ROWS, "proof_checked_view_rows_match_with_work")
assert "source_work > proof_replay_summary_source_work_limit()" in rows_with_work
assert all(text in rows_with_work for text in ("view.attempt_rows.count != view.report.results.goal_attempts.count", "view.theorem_rows.count != view.report.analysis_1.theorems.summaries.count", "view.theorem_proof_goal_ids.count != view.report.analysis_1.theorems.proof_goal_ids.count", "proof_checked_view_attempt_row_matches_with_work", "proof_checked_view_theorem_row_matches_with_work"))
for name in ("proof_checked_view_attempt_status", "proof_checked_view_attempt_is_proven", "proof_checked_view_goal_source_admissible", "proof_checked_view_goal_facts_source_admissible"):
    assert "row_matches" in body(VIEW, name), name
theorem_admission_with_work = body(VIEW, "proof_checked_view_theorem_source_admission_with_work")
assert "proof_checked_view_theorem_row_matches_with_work(view, theorem_index, source_work)" in theorem_admission_with_work
assert "proof_checked_view_theorem_source_admission_with_work(view, theorem_index, &source_work)" in body(VIEW, "proof_checked_view_theorem_source_admission")
THEOREM_OUTPUT = ROOT / "src/app/theorem_output.elisa"
THEOREM_SUGGESTIONS = ROOT / "src/app/theorem_output_suggestions.elisa"
assert "proof_checked_view_theorem_source_admission_with_work(checked_view, theorem_index, &work)" in body(THEOREM_OUTPUT, "proof_declaration_gap_index_build")
assert "proof_checked_view_theorem_source_admission_with_work(checked_view, index, &replay_work)" in body(THEOREM_OUTPUT, "proof_push_json_theorem_catalog_with_replayed")
assert "proof_checked_view_theorem_source_admission_with_work(checked_view, theorem_index, &replay_work)" in body(THEOREM_SUGGESTIONS, "proof_push_json_suggestions_with_replayed")
view_source = VIEW.read_text(encoding="utf-8")
def visibility_at(name: str) -> str:
    accessor_start = view_source.index(f"def {name}[")
    visibility_prefix = view_source[:accessor_start]
    return "private" if visibility_prefix.rfind("private:") > visibility_prefix.rfind("public:") else "public"


for read_only_name in (
    "proof_checked_view_source",
    "proof_checked_view_literal_inventory",
):
    assert visibility_at(read_only_name) == "public", read_only_name
assert visibility_at("proof_checked_view_enum_annotations") == "private"
assert visibility_at("proof_checked_view_diagnostic_report") == "private"
assert visibility_at("proof_checked_view_file") == "private"
assert visibility_at("proof_checked_view_assert_by_inventory") == "private"
assert "def proof_source_analysis_file[" not in view_source
assert "def proof_source_analysis_assert_by_inventory[" not in view_source
public_return_signatures = []
visibility = "private"
for line in view_source.splitlines():
    if line.strip() in ("public:", "private:"):
        visibility = line.strip()[:-1]
    if visibility == "public" and re.match(r"\s*def proof_(?:checked_view|source_analysis)_", line):
        public_return_signatures.append(line)
assert public_return_signatures
for signature in public_return_signatures:
    return_type = signature.partition("->")[2]
    assert "ProofReport&" not in return_type, signature
    assert "Ast::File&" not in return_type, signature
    assert "Ast::Expr&" not in return_type, signature
    assert "darray[(" not in return_type or "Ast::Expr" not in return_type, signature

# Keep authority-bearing fields encapsulated. Public payload projections are read-only borrows;
# the deep mutable report stays private, and status decisions remain available only through the
# receipt-bound verdict methods.
checked_view = struct_body(RECEIPT, "ProofCheckedView")
assert re.search(r"^\s+private:\s*$", checked_view, re.M)
assert re.search(r"^\s+public:\s*$", checked_view, re.M) is None
assert "theorem_proof_goal_ids: darray[usize] = []" in checked_view
for signature in public_return_signatures:
    return_type = signature.partition("->")[2]
    if "& @" in return_type:
        assert "mutable" not in return_type, signature

assert "view.attempt_rows[attempt_index]" in body(VIEW_ATTEMPTS, "proof_checked_view_attempt_diagnostic")
assert "view.theorem_rows[theorem_index]" in body(VIEW, "proof_checked_view_theorem_diagnostic")
assert "proof_checked_view_rows_match(view)" in body(VIEW, "proof_checked_view_source_complete")
print("checked-view row authority guards: exact snapshots gate receipt verdicts")
