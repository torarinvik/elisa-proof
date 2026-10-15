"""Keep public tactic verdicts tied to the source-bound admission capability."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/app/cli_tactics.elisa"
CHECKED_VIEW = ROOT / "src/proof/model/checked_view.elisa"
REPLAY_API = ROOT / "src/proof/replay/api.elisa"
CLI_SUPPORT = ROOT / "src/app/cli_support.elisa"
OUTPUT_STATUS = ROOT / "src/app/output_replay_status.elisa"


def function_body(name: str) -> str:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = [line]
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"function {name} not found in {SOURCE}")


admission = function_body("proof_tactic_result_admitted")
assert "result.valid and result.certificate_replayed and source_match" in admission
assert "target_bound and target_admission_base and target_source_admitted" in admission
assert "not target_bound and source_complete" in admission
assert "target_fingerprint_match" in admission

serializer = function_body("proof_push_json_tactic_result")
assert "admitted: bool = proof_tactic_result_admitted(result, checked_view, source_match, target_bound, target_goal_id, target_fingerprint_match)" in serializer
assert 'proof_push_json_string(buffer, "proved" if admitted else "failed")' in serializer
# Nested tactic status is the script-local replay result; only the outer status includes the
# bound target's source goal/fact admission (or the whole-source portable admission gate).
assert 'proof_push_json_string(buffer, "proved" if tactic_admitted else "failed")' in serializer
assert 'source_admissible: bool = proof_checked_view_target_admission_base(checked_view) if target_bound else proof_checked_view_source_admissible(checked_view)' in serializer
assert 'target_source_admitted: bool = target_bound and proof_checked_view_goal_source_admissible(checked_view, target_goal_id) and proof_checked_view_goal_facts_source_admissible(checked_view, target_goal_id)' in serializer

checked_view_text = CHECKED_VIEW.read_text(encoding="utf-8")
source_complete_start = checked_view_text.index("def proof_checked_view_source_complete")
source_complete_end = checked_view_text.index("def proof_checked_view_source_admissible", source_complete_start)
source_complete = checked_view_text[source_complete_start:source_complete_end]
assert "not view.receipt.source_report_admissible" in source_complete
assert "view.receipt.source_report_complete" in source_complete

# The report-level bit begins with semantic and replay admissibility, then later
# source-goal/fact/theorem snapshots can only revoke it.
source_snapshot_start = checked_view_text.index("def proof_source_analysis_report_admission_snapshot")
source_snapshot = checked_view_text[source_snapshot_start:checked_view_text.index(
    "def proof_source_analysis_goal_admission_snapshot", source_snapshot_start
)]
assert "source_admissible: bool = semantic_admissible and replay_complete" in source_snapshot
assert "source_checks_complete and replay_complete, source_admissible" in source_snapshot
api_lines = REPLAY_API.read_text(encoding="utf-8").splitlines()
api_start = next(i for i, line in enumerate(api_lines) if re.match(r"\s*def proof_check_and_replay_with_source\b", line))
api_body = "\n".join(api_lines[api_start:])
initial_admission = "receipt.source_report_admissible <- source_admission_snapshot.source_admissible"
fact_revocation = "receipt.source_report_admissible <- false if not attempt_fact_snapshot.complete or not attempt_fact_snapshot.claims_admissible"
theorem_revocation = "if not theorem_source_snapshot.complete or not theorem_source_snapshot.claims_admissible:"
assert initial_admission in api_body and fact_revocation in api_body and theorem_revocation in api_body
assert api_body.index(initial_admission) < api_body.index(fact_revocation) < api_body.index(theorem_revocation)

# The process exit code is an acceptance surface too; local goal status alone must
# not authorize exit zero when report-level source checks are incomplete.
cli_support = CLI_SUPPORT.read_text(encoding="utf-8")
assert 'return 0 if state.complete and state.state == "proved" and proof_checked_view_source_admissible(checked_view) and source_admissions_complete else 1' in cli_support
engine_state = OUTPUT_STATUS.read_text(encoding="utf-8").split("def proof_report_engine_state_from_status", 1)[1].split("def proof_goal_state_from_finding_selection", 1)[0]
assert "proof_checked_view_replay_complete(checked_view)" in engine_state
assert "proof_checked_view_source_checks_complete(checked_view)" in engine_state
assert "proof_checked_view_source_admissible(checked_view)" in engine_state
assert "proof_checked_view_source_admissions_complete(checked_view)" in engine_state

print("tactic output authority: public status remains tied to checked source admission")
