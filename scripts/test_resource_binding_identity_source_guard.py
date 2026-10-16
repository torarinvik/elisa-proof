"""Keep resource event identities tied to parser-owned binding scopes."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"missing function {name} in {path}")


resource_identity_path = ROOT / "src/proof/replay/resource_binding_identity_validation.elisa"
resource_identity = resource_identity_path.read_text(encoding="utf-8")
resource_owner = function_body(
    ROOT / "src/proof/replay/resource_call_source_validation.elisa",
    "proof_replay_resource_safety_owner_valid_with_work",
)
assert "proof_replay_resource_binding_position_index_build_with_work(report, root, source_work)" in resource_owner
assert "proof_replay_resource_binding_identities_source_valid_with_work(report, root, resource_positions.index, parameters, body, source_work)" in resource_owner
resource_identity_pass = function_body(
    resource_identity_path, "proof_replay_resource_binding_identities_source_valid_with_work"
)
assert 'report.analysis_1.kernel.nodes[event_root].auxiliary <- 0' in resource_identity_pass
assert "proof_replay_resource_binding_statements_covered_with_work(report, index, names, binders, body" in resource_identity_pass
resource_event_walk = function_body(
    resource_identity_path, "proof_replay_resource_binding_positions_at_with_work"
)
assert 'event.kind in {"resource-safety", "resource-scope", "resource-alternatives"}' in resource_event_walk
resource_scope_mark = function_body(
    resource_identity_path, "proof_replay_resource_binding_scope_mark_with_work"
)
resource_scope_restore = function_body(
    resource_identity_path, "proof_replay_resource_binding_scope_restore_with_work"
)
assert "names.count != binders.count" in resource_scope_mark
assert "(true, names.count)" in resource_scope_mark
assert "mark > names.count" in resource_scope_restore
assert "names <- names.truncate(mark)" in resource_scope_restore
assert "binders <- binders.truncate(mark)" in resource_scope_restore
resource_statement_walk = function_body(
    resource_identity_path, "proof_replay_resource_binding_statements_covered_with_work"
)
assert "branch_scope.mark, source_work" in resource_statement_walk
assert "nested_scope.mark, source_work" in resource_statement_walk
assert "proof_replay_resource_binding_range_shape_with_work(iterable, source_work, 0)" in resource_statement_walk
assert 'proof_replay_resource_binding_position_find_with_work(report, index, "resource-bind", iterable_position.end_offset.usize(), variable' in resource_statement_walk
for operation in ("resource-use", "resource-write", "resource-move"):
    assert f'"{operation}"' in resource_identity_pass
assert '"resource-region-assign"' in resource_identity_pass
assert 'proof_replay_resource_binding_position_find_with_work(report, index, "resource-bind", position.end_offset.usize(), name' in resource_identity
assert 'proof_replay_resource_binding_event_annotate_with_work(report, index, "resource-write"' in resource_identity
assignment_index = function_body(resource_identity_path, "proof_replay_resource_binding_positions_at_with_work")
assert '"resource-region-assign"' in assignment_index
assignment_annotate = function_body(resource_identity_path, "proof_replay_resource_binding_assignment_annotate_with_work")
assert '"resource-region-assign"' in assignment_annotate
assert "nodes[event_root].right <- source_identity" in assignment_annotate
assert "nodes[event_root].auxiliary <- target_identity" in assignment_annotate
assignment_statement_walk = function_body(resource_identity_path, "proof_replay_resource_binding_statements_covered_with_work")
assert 'proof_replay_resource_binding_position_kind_count_at_with_work(index, "resource-region-assign"' in assignment_statement_walk
assert "source_binding.identity, binding.identity" in assignment_statement_walk
resource_kernel = (ROOT / "src/proof/kernel_replay/resource_events.elisa").read_text(encoding="utf-8")
assert resource_kernel.count("proof_kernel_replay_resource_binding_event_identity_matches(state, nodes, slot, node.auxiliary)") >= 3
assignment_kernel = function_body(
    ROOT / "src/proof/kernel_replay/resource_events.elisa", "proof_kernel_replay_resource_events_remaining"
)
assert 'node.right != state.bindings.binding_event_roots[source_slot] + 1' in assignment_kernel
assert 'node.auxiliary != state.bindings.binding_event_roots[target_slot] + 1' in assignment_kernel
assert "source_slot, node.right" in assignment_kernel
assignment_producer = function_body(
    ROOT / "src/proof/resources/region_flow.elisa", "proof_resource_handle_region_assignment"
)
assert "target_event_root + 1" in assignment_producer
assert "source_event_root + 1" in assignment_producer
assert "nodes[event].right <- source_identity" in assignment_producer
assignment_shape = function_body(
    ROOT / "src/proof/kernel_replay/resource_region_assignment_shape.elisa",
    "proof_kernel_replay_arena_resource_region_assignment_shape",
)
assert "node.right > 0" in assignment_shape and "node.auxiliary > 0" in assignment_shape
resource_identity_kernel = function_body(
    ROOT / "src/proof/kernel_replay/resource_state.elisa",
    "proof_kernel_replay_resource_binding_event_identity_matches",
)
assert 'nodes[root].kind not in {"resource-bind", "resource-region-alloc", "resource-region-bind", "resource-call-result"}' in resource_identity_kernel
assert "nodes[root].name == state.bindings.binding_names[slot]" in resource_identity_kernel

# Global field places have no declaration-derived storage identity yet. Keep the
# producer refusal explicit: an untracked write or borrow must fail source
# admission instead of disappearing from the local binding trace.
resource_write = function_body(
    ROOT / "src/proof/resources/region_flow.elisa", "proof_resource_check_write"
)
assert 'if root == "":' in resource_write
assert 'proof_resource_add_failing_obligation(report, "resource-write-opaque"' in resource_write
missing_root = resource_write.split('if root == "":', 1)[1].split("\n            binding:", 1)[0]
assert 'proof_resource_add_failing_obligation(report, "resource-write-opaque", position, function_name, "a write target without a tracked storage root cannot be checked safely")' in missing_root
assert missing_root.strip().endswith("return")
lookup_failure = resource_write.split("if not binding.complete:", 1)[1].split("if binding.slot", 1)[0]
assert 'proof_add_budget_finding(report, "resource-analysis-budget"' in lookup_failure
assert "resource write root lookup exceeded its shared source-work budget" in lookup_failure
assert "return" in lookup_failure
assert "binding.slot >= state.bindings.binding_names.count" in resource_write
assert "a write to storage outside the tracked function resource frame cannot be checked safely" in resource_write
outside_frame = resource_write.split("if binding.slot >= state.bindings.binding_names.count:", 1)[1].split("\n            slot:", 1)[0]
assert 'proof_resource_add_failing_obligation(report, "resource-write-opaque", position, function_name, "a write to storage outside the tracked function resource frame cannot be checked safely")' in outside_frame
assert outside_frame.strip().endswith("return")
assert "proof_resource_record_event" not in outside_frame

resource_bind = function_body(
    ROOT / "src/proof/resources/statement_bindings.elisa", "proof_resource_check_var"
)
assert "not target_binding.complete or target_slot >= state.bindings.binding_names.count" in resource_bind
assert 'proof_resource_add_failing_obligation(report, "borrow-source-opaque"' in resource_bind
assert "state.bindings.binding_type_marker_complete[opaque_slot] <- false" in resource_bind

local_borrow_gate = function_body(
    ROOT / "src/proof/replay/resource_write_coverage.elisa",
    "proof_replay_resource_local_borrows_absent_at_with_work",
)
assert 'if event.kind == "resource-bind":' in local_borrow_gate
assert "return event.operator == \"value\"" in local_borrow_gate

failing_obligation = function_body(
    ROOT / "src/proof/resources/borrows_and_bindings.elisa",
    "proof_resource_add_failing_obligation",
)
assert "report.proof_obligation(false)" in failing_obligation
assert "proof_add_finding(report, kind" in failing_obligation
report_recording = ROOT / "src/proof/model/report_recording.elisa"
budget_finding = function_body(report_recording, "proof_add_budget_finding")
assert "proof_add_finding(report, kind, line, name, message)" in budget_finding
finding_body = function_body(report_recording, "proof_add_finding")
assert "report.results.failed <- report.results.failed + 1" in finding_body
source_snapshot = function_body(
    ROOT / "src/proof/model/checked_view_admission.elisa",
    "proof_source_analysis_report_admission_snapshot",
)
assert "report.results.failed == 0" in source_snapshot
assert "report.results.producer_proven_count == report.results.obligations" in source_snapshot
assert "source_checks_complete and replay_complete" in source_snapshot
replay_api = function_body(ROOT / "src/proof/replay/api.elisa", "proof_check_and_replay_with_source")
assert "receipt.source_report_complete <- source_admission_snapshot.source_complete" in replay_api
assert "receipt.source_report_complete <- false if not attempt_fact_snapshot.complete or not attempt_fact_snapshot.claims_admissible" in replay_api
checked_view_source_complete = function_body(
    ROOT / "src/proof/model/checked_view.elisa", "proof_checked_view_source_complete"
)
assert checked_view_source_complete.rstrip().endswith("view.receipt.source_report_complete")
source_report_admission = function_body(
    ROOT / "src/proof/model/checked_view.elisa",
    "proof_checked_view_source_admissible",
)
assert "return false if not proof_checked_view_source_complete(view)" in source_report_admission

print("resource binding identity guard: parser scopes, kernel live slots, and report-level opaque-place refusal remain linked")
