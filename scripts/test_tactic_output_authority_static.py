"""Keep public tactic verdicts tied to the source-bound admission capability."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/app/cli_tactics.elisa"
CHECKED_VIEW = ROOT / "src/proof/model/checked_view.elisa"
CHECKED_VIEW_ROWS = ROOT / "src/proof/model/checked_view_rows.elisa"
CHECKED_VIEW_ADMISSION = ROOT / "src/proof/model/checked_view_admission.elisa"
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
assert "admitted: bool = proof_tactic_result_admitted(result, status, source_match, target_bound, target_fingerprint_match)" in serializer
assert 'proof_push_json_string(buffer, "proved" if admitted else "failed")' in serializer
# Nested tactic status is the script-local replay result; only the outer status includes the
# bound target's source goal/fact admission (or the whole-source portable admission gate).
assert 'proof_push_json_string(buffer, "proved" if tactic_admitted else "failed")' in serializer
assert 'source_admissible: bool = status.target_admission_base if target_bound else status.source_admissible' in serializer
assert 'target_source_admitted: bool = target_bound and status.source_admitted' in serializer

# Tactic replay and final serialization reuse one source/target snapshot under the caller's
# aggregate meter instead of restarting whole-report row comparisons for each scalar query.
status_snapshot = CHECKED_VIEW_ROWS.read_text(encoding="utf-8").split(
    "def proof_checked_view_tactic_status_snapshot_with_work", 1
)[1].split("def proof_checked_view_attempt_status_snapshot_with_work", 1)[0]
assert "proof_checked_view_rows_match_with_work(view, source_work)" in status_snapshot
assert "source_complete: bool =" in status_snapshot
assert "target_admission_base: bool =" in status_snapshot
assert "source_admitted: bool = goal_source_admitted and facts_source_admitted" in status_snapshot
assert "proven <- proof_replay_receipt_attempt_is_proven(view.receipt, attempt_index)" in status_snapshot
goal_source_snapshot = CHECKED_VIEW_ROWS.read_text(encoding="utf-8").split(
    "def proof_checked_view_goal_source_admissions_with_work", 1
)[1].split("def proof_checked_view_tactic_status_snapshot_with_work", 1)[0]
assert "proof_checked_view_attempt_row_matches_with_work(view, attempt_index, source_work)" in goal_source_snapshot
assert "goal_admitted and facts_admitted" in goal_source_snapshot
tactic_run = (ROOT / "src/proof/tactic_json.elisa").read_text(encoding="utf-8").split(
    "def proof_tactic_json_run_source_with_status", 1
)[1].split("def proof_tactic_json_run_source[", 1)[0]
assert "proof_checked_view_tactic_status_snapshot_with_work(checked_view, goal_id, source_work)" in tactic_run
assert "not status.complete or not status.source_admitted" in tactic_run
target_run = (ROOT / "src/proof/tactic_json.elisa").read_text(encoding="utf-8").split(
    "def proof_tactic_json_run_source_with_target_work", 1
)[1].split("def proof_tactic_json_run_source[", 1)[0]
assert "proof_checked_view_goal_source_admissions_with_work(checked_view, goal_id, source_work)" in target_run
assert "not status.complete or not status.source_admitted" in target_run
assert "source_admitted: bool)" in target_run
repair_check = (ROOT / "src/app/repair.elisa").read_text(encoding="utf-8").split(
    "def proof_repair_check_candidate", 1
)[1].split("def proof_repair_push_actions", 1)[0]
assert "source_work: mutable usize&" in repair_check
assert "proof_tactic_json_run_source_with_target_work" in repair_check
assert "usable <- candidate_run.source_admitted" in repair_check
cli_run = SOURCE.read_text(encoding="utf-8")
assert "proof_tactic_json_run_source_with_status" in cli_run
assert "if not tactic_status_ready:" in cli_run
assert "proof_checked_view_tactic_status_snapshot_with_work(checked_view, target_goal_id, &tactic_status_work)" in cli_run
assert "target_previously_proven <- tactic_status.proven if target_bound and source_target.valid and target_goal_id < report.results.goal_attempts.count" in cli_run

checked_view_text = CHECKED_VIEW.read_text(encoding="utf-8")
source_complete_start = checked_view_text.index("def proof_checked_view_source_complete")
source_complete_end = checked_view_text.index("def proof_checked_view_source_admissible", source_complete_start)
source_complete = checked_view_text[source_complete_start:source_complete_end]
assert "not view.receipt.source_report_admissible" in source_complete
assert "view.receipt.source_report_complete" in source_complete

# The report-level bit begins with semantic and replay admissibility, then later
# source-goal/fact/theorem snapshots can only revoke it.
admission_text = CHECKED_VIEW_ADMISSION.read_text(encoding="utf-8")
source_snapshot_start = admission_text.index("def proof_source_analysis_report_admission_snapshot")
source_snapshot = admission_text[source_snapshot_start:admission_text.index(
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

report_status = OUTPUT_STATUS.read_text(encoding="utf-8").split("def proof_report_verification_state_from_findings", 1)[1].split("def proof_report_engine_state_from_status", 1)[0]
report_incomplete_gate = (
    'return "unknown" if not finding_counts.complete or not source_checks_complete '
    'or not source_complete or not source_admissible or not source_admissions_complete '
    'or not replay_complete'
)
assert report_status.index(report_incomplete_gate) < report_status.index('return "disproved" if finding_counts.disproved > 0')

finding_counts = OUTPUT_STATUS.read_text(encoding="utf-8").split(
    "def proof_output_finding_counts_with_work", 1
)[1].split("def proof_report_verification_state_from_findings", 1)[0]
assert "status_length: usize = sview_len(finding.status)" in finding_counts
assert finding_counts.index(
    "proof_output_reserve_status_snapshot_work(work_used, 2)"
) < finding_counts.index("status_length: usize = sview_len(finding.status)")
assert finding_counts.index(
    "proof_output_reserve_status_snapshot_work(work_used, 9)"
) < finding_counts.index('finding.status == "disproved"')
assert finding_counts.index(
    "proof_output_reserve_status_snapshot_work(work_used, 11)"
) < finding_counts.index('finding.status == "unsupported"')
assert "if status_length == 9 and finding.status == \"disproved\":" in finding_counts
assert "elif status_length == 11 and finding.status == \"unsupported\":" in finding_counts
assert "goal_snapshot: (complete: bool, replayed_goals: darray[bool], source_admitted_goals: darray[bool]" in finding_counts
assert "proof_output_checked_view_goal_statuses_with_work(checked_view, work_used)" in finding_counts
assert "not goal_snapshot.complete" in finding_counts
assert "proof_output_cached_source_admission_status(goal_snapshot.source_admitted_goals, finding.goal_id)" in finding_counts
assert "unsupported <- unsupported + 1 if not finding.has_goal or unsupported_source_admitted" in finding_counts
assert "unknown <- unknown + 1 if finding.has_goal and not unsupported_source_admitted" in finding_counts
assert "# Timeout is preserved only by the goal-specific status API." in finding_counts
assert finding_counts.rstrip().endswith("unknown <- unknown + 1\n            return (true, disproved, unsupported, unknown)")

attempt_status = CHECKED_VIEW_ROWS.read_text(encoding="utf-8").split(
    "def proof_checked_view_attempt_status_snapshot_with_work", 1
)[1].split("\n        def ", 1)[0]
assert "goal_source_admitted: bool = view.receipt.source_goal_statuses[attempt_index]" in attempt_status
assert "facts_source_admitted: bool = view.receipt.source_attempt_fact_statuses[attempt_index]" in attempt_status
assert "source_admitted: bool = goal_source_admitted and facts_source_admitted" in attempt_status

print("tactic output authority: public status remains tied to checked source admission")
