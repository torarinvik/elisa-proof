"""Keep mutable report diagnostics out of source-authorized proof verdicts."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = [line]
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"function {name} not found in {path}")


def visibility_before(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    definition = next(i for i, line in enumerate(lines) if re.match(rf"\s*def {re.escape(name)}\b", line))
    indent = len(lines[definition]) - len(lines[definition].lstrip())
    for index in range(definition - 1, -1, -1):
        stripped = lines[index].strip()
        current_indent = len(lines[index]) - len(lines[index].lstrip())
        if current_indent < indent and stripped in {"private:", "public:"}:
            return stripped[:-1]
    raise AssertionError(f"visibility for {name} not found")


receipt_model = ROOT / "src/proof/model/replay_receipt.elisa"
receipt_text = receipt_model.read_text(encoding="utf-8")
for type_name in ("ProofReplayReceipt", "ProofSourceAnalysis", "ProofCheckedView"):
    assert re.search(rf"struct {type_name}\[@r\]:\n\s+private:", receipt_text), type_name

checked_view = ROOT / "src/proof/model/checked_view.elisa"
app_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src/app").rglob("*.elisa"))
assert not re.search(r"\.producer_proven\b|\.producer_proven_count\b|\.proven\b", app_text)
struct_invariant_scan = function_body(checked_view, "proof_source_struct_invariant_scan")
assert "Ast::Decl.Struct(_, _, _, _, _, invariants, _)" in struct_invariant_scan
assert "invariants.count > 0" in struct_invariant_scan
assert "proof_source_analysis_charge_work(invariants.count, source_work)" in struct_invariant_scan
assert "proof_source_struct_invariant_scan(nested, source_work, depth + 1)" in struct_invariant_scan
assert "_:\n                        return (false, false)" in struct_invariant_scan
source_admission = function_body(checked_view, "proof_source_analysis_report_admission_snapshot")
assert "not source.source_struct_invariant_scan_complete" in source_admission
struct_failure = source_admission.index('"unsupported-source-struct-invariant"')
struct_refusal = source_admission.index("source.source_has_struct_invariants")
assert struct_failure < struct_refusal < source_admission.index("proof_report_source_postcondition_inventory_consistent_with_work")
source_import = function_body(checked_view, "proof_source_analysis_import_parse")
struct_scan = source_import.index("proof_source_struct_invariant_scan(top_declarations, &inventory_source_work, 0)")
assert struct_scan < source_import.index("proof_source_literal_ensure_inventory_with_work")
assert "source_struct_invariant_scan_complete: struct_invariant_scan.complete" in source_import
assert "source_has_struct_invariants: struct_invariant_scan.found" in source_import
assert visibility_before(checked_view, "proof_checked_view_create") == "private"
view_create = function_body(checked_view, "proof_checked_view_create")
for gate in (
    "not receipt.issued or not source.issued",
    "not report.source.source_analysis_bound",
    "receipt.source_identity != source.source_identity",
    "receipt.source_file_identity != source.file_identity",
    "receipt.source_bytes != source.source_bytes",
    "receipt.source_fingerprint != source.source_fingerprint",
    "fact_call_snapshot.status.source_identity != source.file_identity",
    "fact_call_snapshot.status.source_fingerprint != source.source_fingerprint",
):
    assert gate in view_create, gate
diagnostic_report = function_body(checked_view, "proof_checked_view_diagnostic_report")
assert "ProofReport& @view" in diagnostic_report
assert visibility_before(checked_view, "proof_checked_view_diagnostic_report") == "public"

source_complete = function_body(checked_view, "proof_checked_view_source_complete")
for gate in (
    "proof_checked_view_source_validated(view)",
    "view.receipt.source_admission_snapshot_complete",
    "view.receipt.source_goal_statuses_complete",
    "view.receipt.source_claims_admissible",
    "view.receipt.source_report_complete",
):
    assert gate in source_complete, gate
source_admissible = function_body(checked_view, "proof_checked_view_source_admissible")
assert "proof_checked_view_source_complete(view)" in source_admissible
assert "view.receipt.source_report_admissible" in source_admissible
attempt_proven = function_body(checked_view, "proof_checked_view_attempt_is_proven")
for gate in (
    "proof_checked_view_source_validated(view)",
    "proof_checked_view_goal_source_admissible(view, attempt_index)",
    "proof_checked_view_goal_facts_source_admissible(view, attempt_index)",
    "proof_replay_receipt_attempt_is_proven(view.receipt, attempt_index)",
):
    assert gate in attempt_proven, gate

replay_api = ROOT / "src/proof/replay/api.elisa"
kernel_only = function_body(replay_api, "proof_replay_receipt_kernel_attempt_status")
assert "not receipt.source_bound" not in kernel_only
assert "Low-trust standalone replay diagnostic" in replay_api.read_text(encoding="utf-8")
source_proven = function_body(replay_api, "proof_replay_receipt_attempt_is_proven")
for gate in ("receipt.source_bound", "receipt.source_validated", "attempt_index >= receipt.attempt_proven_statuses.count"):
    assert gate in source_proven, gate
standalone_replay = function_body(replay_api, "proof_replay_certificates")
assert "proof_replay_receipt_from_report(report, false)" in standalone_replay
receipt_complete = function_body(replay_api, "proof_replay_receipt_is_complete")
for gate in ("receipt.issued", "receipt.source_bound", "receipt.source_validated", "receipt.complete"):
    assert gate in receipt_complete, gate
assert visibility_before(replay_api, "proof_replay_receipt_from_report") == "private"
receipt_issuer = function_body(replay_api, "proof_replay_receipt_from_report")
assert "source_validated: bool" in receipt_issuer
checked_transaction = function_body(replay_api, "proof_check_and_replay_with_source")
assert "proof_replay_receipt_from_report(report, false)" in checked_transaction
binding = checked_transaction.split("if source_structure_failure == \"\":", 1)[1].split("goal_finding_clear:", 1)[0]
for gate in (
    "receipt.source_identity <- source_identity",
    "receipt.source_file_identity <- source_file_identity",
    "receipt.source_bytes <- source_bytes",
    "receipt.source_fingerprint <- source_fingerprint",
    "receipt.source_bound <- true",
    "receipt.source_validated <- true",
):
    assert gate in binding, gate

invariants = ROOT / "src/proof/model/report_invariants.elisa"
assert visibility_before(invariants, "proof_report_all_obligations_proven") == "private"
legacy_diagnostic = function_body(invariants, "proof_report_source_has_unresolved_checks")
assert "Legacy report diagnostic" in invariants.read_text(encoding="utf-8")
assert "proof_report_all_obligations_proven(report)" in legacy_diagnostic

checked_source_admissions = function_body(checked_view, "proof_checked_view_source_admissions_complete")
for gate in ("proof_checked_view_goal_source_admissions_complete(view)",
             "proof_checked_view_theorem_source_admissions_complete(view)"):
    assert gate in checked_source_admissions, gate

# Serializer-facing producer fields remain diagnostics: emitted per-goal proof status must be
# conjoined with replay and source-admission snapshots, and those snapshots come from the checked
# view rather than report counters or producer flags.
status_helpers = ROOT / "src/app/output_replay_status.elisa"
goal_snapshot = function_body(status_helpers, "proof_output_checked_view_goal_statuses_with_work")
for gate in (
    "proof_checked_view_attempt_status(checked_view, goal_id)",
    "proof_checked_view_goal_source_admissible(checked_view, goal_id)",
    "proof_checked_view_goal_facts_source_admissible(checked_view, goal_id)",
):
    assert gate in goal_snapshot, gate

report_output = ROOT / "src/app/report_output_integrated_helpers.elisa"
summary_output = function_body(report_output, "proof_push_json_report_summary_with_replay")
full_report_output = function_body(report_output, "proof_push_json_report_with_replay")
for serializer in (summary_output, full_report_output):
    assert "verdict <- \"failed\" if not effective_source_admissible" in serializer
    assert 'proof_push_json_string(buffer, verdict)' in serializer
source_admission_matrix = (ROOT / "scripts/test_source_admission_matrix.py").read_text(encoding="utf-8")
assert '"summary-json"' in source_admission_matrix and '"json"' in source_admission_matrix
assert 'assert source["admissible"] is False' in source_admission_matrix
assert 'payload["status"] == "failed"' in source_admission_matrix
engine_state = function_body(status_helpers, "proof_report_engine_state_from_status")
for gate in ("proof_checked_view_replay_complete(checked_view)",
             "proof_checked_view_source_checks_complete(checked_view)",
             "proof_checked_view_source_admissible(checked_view)",
             "proof_checked_view_source_admissions_complete(checked_view)"):
    assert gate in engine_state, gate
exit_gate = function_body(ROOT / "src/app/cli_support.elisa", "proof_goal_route_exit_with_state")
for gate in ("state.complete", 'state.state == "proved"',
             "proof_checked_view_source_admissible(checked_view)",
             "proof_checked_view_goal_source_admissions_complete(checked_view)"):
    assert gate in exit_gate, gate
serialized_goals = function_body(report_output, "proof_push_json_report_with_replay")
assert (
    "replay_proven: bool = producer_claim and "
    "proof_output_cached_replay_status(replayed_goals, index) and "
    "proof_output_cached_source_admission_status(source_admitted_goals, index)"
) in serialized_goals
assert "producer_claim: bool = proof_output_cached_producer_claim_status(producer_claimed_goals, index)" in serialized_goals
assert 'proof_push(buffer, "true" if replay_proven else "false")' in serialized_goals

theorem_output = ROOT / "src/app/theorem_output.elisa"
serialized_theorem = function_body(theorem_output, "proof_push_json_theorem")
assert "proof_push(buffer, \"true\" if kernel_verified and source_claim_admissible else \"false\")" in serialized_theorem
assert "source_claim_admissible: bool = theorem_source_admissible and source_admissions_complete and declaration_identity_unambiguous and valid_proof_goals" in serialized_theorem
assert 'proof_push(buffer, "true" if replayed and proof_output_cached_source_admission_status(source_admitted_goals, goal_id) else "false")' in serialized_theorem

package_output = ROOT / "src/app/package_output.elisa"
serialized_package = function_body(package_output, "proof_push_json_package_with_replayed")
assert "proof_checked_view_source_admissible(checked_view)" in serialized_package
assert "not proof_output_cached_producer_claim_status(producer_claimed_goals, goal_id) or not proof_output_cached_replay_status(replayed_goals, goal_id) or not proof_output_cached_source_admission_status(source_admitted_goals, goal_id)" in serialized_package

source_map = ROOT / "src/app/source_map_output.elisa"
serialized_functions = function_body(source_map, "proof_push_json_function_status_from_checked_view")
assert "proof_output_checked_view_goal_status_with_work(checked_view, goal_id, work_used)" in serialized_functions
assert "proof_checked_view_source_admissible(checked_view) and proof_checked_view_source_admissions_complete(checked_view)" in serialized_functions
assert 'source_authority_complete and open_goals[index] == 0 and findings[index] == 0' in serialized_functions
single_goal_snapshot = function_body(status_helpers, "proof_output_checked_view_goal_status_with_work")
assert "proof_checked_view_goal_source_admissible(checked_view, goal_id)" in single_goal_snapshot
assert "proof_checked_view_goal_facts_source_admissible(checked_view, goal_id)" in single_goal_snapshot

explain_output = ROOT / "src/app/explain_output.elisa"
explained_goal = function_body(explain_output, "proof_push_goal_explanation_with_replayed")
assert "producer_claim: bool = goal_status.producer_claimed" in explained_goal
assert 'goal_state_result.state == "proved" and producer_claim and replayed and source_admitted' in explained_goal

print("source authority guards: opaque receipt, source admission, and low-trust replay paths stay distinct")
