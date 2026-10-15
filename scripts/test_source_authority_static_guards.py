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
goal_admission_snapshot = function_body(checked_view, "proof_source_analysis_goal_admission_snapshot")
assert "not source.source_struct_invariant_scan_complete or source.source_has_struct_invariants" in goal_admission_snapshot
assert "proof_report_source_goal_finding_snapshot(report, source_work)" in goal_admission_snapshot
finding_snapshot_path = ROOT / "src/proof/model/report_goal_finding_snapshot.elisa"
finding_snapshot = function_body(finding_snapshot_path, "proof_report_source_goal_finding_snapshot")
assert "finding.has_goal and finding.goal_id >= report.results.goal_attempts.count" in finding_snapshot
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
assert "mutable ProofReport&" not in diagnostic_report
assert visibility_before(checked_view, "proof_checked_view_diagnostic_report") == "public"

source_complete = function_body(checked_view, "proof_checked_view_source_complete")
for gate in (
    "proof_checked_view_source_validated(view)",
    "view.receipt.source_admission_snapshot_complete",
    "view.receipt.source_goal_statuses_complete",
    "view.receipt.source_claims_admissible",
    "view.receipt.theorem_source_admissions_complete",
    "view.receipt.theorem_source_admissions.count != view.report.analysis_1.theorems.summaries.count",
    "view.receipt.source_report_complete",
):
    assert gate in source_complete, gate
source_admissible = function_body(checked_view, "proof_checked_view_source_admissible")
assert "proof_checked_view_source_complete(view)" in source_admissible
assert "view.receipt.source_report_admissible" in source_admissible
target_admission = function_body(checked_view, "proof_checked_view_target_admission_base")
for gate in (
    "view.receipt.theorem_source_admissions_complete",
    "view.receipt.theorem_source_admissions.count != view.report.analysis_1.theorems.summaries.count",
):
    assert gate in target_admission, gate
source_checks = function_body(checked_view, "proof_checked_view_source_checks_complete")
for gate in (
    "view.receipt.theorem_source_admissions_complete",
    "view.receipt.theorem_source_admissions.count == view.report.analysis_1.theorems.summaries.count",
):
    assert gate in source_checks, gate

# A line number or leaf function name is not a declaration identity: #line directives and
# same-named declarations can make both ambiguous. Keep owner authentication tied to the exact
# parser-owned declaration offset, with a unique source construct/call-site match.
owner_path = ROOT / "src/proof/replay/trace_owner_source_position.elisa"
owner_source = owner_path.read_text(encoding="utf-8")
owner_resolver = function_body(owner_path, "proof_replay_trace_owner_source_position_with_work")
declaration_scan = function_body(owner_path, "proof_replay_trace_owner_source_position_line_in_declarations")
assert "source_position.offset == declaration_position.offset" in declaration_scan
assert "matches != 1" in declaration_scan
assert "proof_replay_trace_owner_signature_requires_call" in declaration_scan
assert "proof_replay_summary_call_exact_span_in_body" in declaration_scan
assert "Ast::Decl.Module(_, nested, _) | Ast::Decl.Scoped(nested, _)" in declaration_scan
assert "matches != 1" in owner_resolver
assert "source_position.end_offset <= source_position.offset" in owner_resolver
assert "source_position.line != certificate.line" in owner_resolver
assert 'matches <- 2' in owner_source  # Ambiguous/unsupported AST paths fail closed.

# Resource call edges use the exact caller declaration identity carried by the resource root,
# and the source offset zero remains valid for declarations at the beginning of a file.
resource_root = function_body(
    ROOT / "src/proof/resources/state_and_regions.elisa", "proof_resource_finish"
)
assert "functions.lookup.lines[function_index].usize()" in resource_root
assert "functions.lookup.offsets[function_index].i64()" in resource_root
resource_shape = function_body(
    ROOT / "src/proof/kernel_replay/arena_shapes.elisa",
    "proof_kernel_replay_arena_resource_summary_shape",
)
assert "node.right > 0" in resource_shape
assert "node.value >= 0 and node.value <= 4294967295" in resource_shape
resource_source_path = ROOT / "src/proof/replay/resource_call_source_validation.elisa"
resource_default = function_body(
    resource_source_path, "proof_replay_resource_default_is_literal_with_work"
)
assert "Ast::Expr.IntLit(_, _) | Ast::Expr.BoolLit(_, _)" in resource_default
assert "Ast::Expr.FloatLit(text, _) | Ast::Expr.CharLit(text, _)" in resource_default
assert "_:\n                    false" in resource_default
resource_omission = function_body(
    ROOT / "src/proof/replay/resource_call_shadow_validation.elisa",
    "proof_replay_resource_call_name_is_irrelevant_with_work",
)
assert "parameter.has_default and not proof_replay_resource_default_is_literal_with_work" in resource_omission
resource_owner = function_body(
    resource_source_path, "proof_replay_resource_safety_owner_valid_with_work"
)
assert "root.value < 0" in resource_owner
assert "root.right == 0" in resource_owner
assert "proof_replay_summary_owner_function_at_offset" in resource_owner
assert "entry.owner != root.secondary_name" in resource_owner
resource_write_producer = function_body(
    ROOT / "src/proof/resources/region_flow.elisa", "proof_resource_check_write"
)
assert "state.evidence.trace_events.count == event_count + 1" in resource_write_producer
assert "report.analysis_1.kernel.nodes[event].value <- position.offset.i64()" in resource_write_producer
resource_write_source_path = ROOT / "src/proof/replay/resource_write_source_validation.elisa"
resource_write_replay = function_body(
    resource_write_source_path, "proof_replay_resource_write_source_valid_with_work"
)
assert "event.value < 0 or event.value > 4294967295" in resource_write_replay
assert "proof_replay_summary_owner_function_at_offset" in resource_write_replay
resource_write_find = function_body(
    resource_write_source_path, "proof_replay_resource_write_find_assignment_with_work"
)
assert "position.offset == offset.u32()" in resource_write_find
for nested_shape in ("Ast::Stmt.If", "Ast::Stmt.While", "Ast::Stmt.For", "Ast::Stmt.Block", "Ast::Stmt.Match"):
    assert nested_shape in resource_write_find
assert "proof_replay_resource_write_find_assignment_with_work(body, event.value.usize()" in resource_write_replay
assert "proof_replay_ast_matches_kernel_with_work(report, source_target, event.left" in resource_write_replay
resource_write_coverage_path = ROOT / "src/proof/replay/resource_write_coverage.elisa"
resource_write_coverage = function_body(
    resource_source_path, "proof_replay_resource_safety_owner_valid_with_work"
)
assert "proof_replay_resource_parameter_writes_covered_with_work(report, root, body, parameters, parameter.name" in resource_write_coverage
resource_prefix_edges = function_body(
    resource_source_path, "proof_replay_resource_prefix_edges_unique_with_work"
)
for guard in (
    "node_count > remaining_work / 3",
    "prefix_end > remaining_work / 2",
    "report.analysis_1.kernel.children.count > remaining_work",
    "prefix_nodes.resize(node_count)",
    "incoming_counts.resize(node_count)",
    "for parent_index in 0..<node_count",
    "for child_offset in 0..<parent.children_count",
    "parent_index != root_index or edge_index < authorized_start or edge_index >= authorized_end",
    "incoming_counts[child] > 1",
    "incoming_counts[child] != 1",
):
    assert guard in resource_prefix_edges, guard
assert "proof_replay_resource_prefix_edges_unique_with_work(report, root_index, root, prefix_end, source_work)" in resource_write_coverage
coverage_text = resource_write_coverage_path.read_text(encoding="utf-8") + (ROOT / "src/proof/replay/resource_event_source_validation.elisa").read_text(encoding="utf-8")
assert "proof_replay_resource_event_count_in_root_with_work" in coverage_text
assert "proof_replay_resource_write_source_root_with_work" in coverage_text
assert 'if wanted_kind == "resource-use" and position.offset == offset.u32()' in coverage_text
assert 'if wanted_kind == "resource-use"' in (ROOT / "src/proof/replay/resource_event_source_validation.elisa").read_text(encoding="utf-8")
assert 'method not in {"push", "extend", "clear", "resize", "pop", "truncate"}' in coverage_text
assert "proof_replay_resource_write_builtin_arguments_valid_with_work(arguments, source_work)" in coverage_text
assert "proof_replay_resource_local_borrows_absent_in_root_with_work(report, root, scan, source_work)" in resource_write_coverage
assert "Ast::Expr.StaticEffectCall(_, _, _, _, _, _):\n                    return false" in coverage_text
assert 'Ast::Stmt.VarDecl(name, type_expression, initializer, position):' in coverage_text
assert "proof_replay_resource_local_value_bind_source_valid_with_work" in (ROOT / "src/proof/replay/certificate_validation.elisa").read_text(encoding="utf-8")
assert 'Ast::Stmt.For(_, _, iterable, nested, _):\n                        return false if not proof_replay_resource_write_builtin_call_covered_with_work(report, root, parameters, index, iterable, parameter_name, source_work, depth + 1)\n                        return false if not proof_replay_resource_parameter_writes_covered_with_work(report, root, nested, parameters, parameter_name, index, source_work, depth + 1)' in coverage_text
assert 'Ast::Expr.RegionNew(_, _, _) | Ast::Expr.Lambda' in coverage_text
assert "receiver_formal_matches != 1" in coverage_text
assert "formal_root_matches != 1" in coverage_text
assert 'proof_replay_resource_parameter_writes_covered_with_work(report, root, body, parameters, "", cache.deterministic_calls.declaration_index' in resource_owner
# The owner-wide mutation scan delegates direct and module-qualified call effects to the
# independent resource-call coverage pass, while keeping unknown method dispatch closed.
write_call_coverage = function_body(resource_write_coverage_path, "proof_replay_resource_write_builtin_call_covered_with_work")
call_clause = write_call_coverage[write_call_coverage.index("Ast::Expr.Call(callee, arguments, _, position):"):write_call_coverage.index("Ast::Expr.StaticEffectCall(_, _, _, _, _, _):")]
assert 'method not in {"push", "extend", "clear", "resize", "pop", "truncate"}' in call_clause
assert 'Ast::Expr.Ident(_, _):' in call_clause
assert 'return false if not proof_replay_resource_write_builtin_call_covered_with_work(report, root, parameters, index, callee' in call_clause
assert 'for argument in arguments |report, root, index, parameter_name, source_work, depth|:' in call_clause
resource_event_facts = function_body(
    ROOT / "src/proof/replay/certificate_validation.elisa",
    "proof_replay_resource_event_facts_with_owner",
)
assert 'if node.kind == "resource-call":' in resource_event_facts
assert 'if node.kind == "resource-call-lend":' in resource_event_facts
assert 'return false' in resource_event_facts[resource_event_facts.index('if node.kind == "resource-call":'):resource_event_facts.index('if node.kind == "resource-write":')]
resource_calls = function_body(
    resource_source_path, "proof_replay_resource_call_site_matches_owner_with_work"
)
assert "owner_line, owner_offset" in resource_calls
assert "caller_entry.owner != owner_module" in resource_calls
assert "proof_replay_resource_call_name_is_irrelevant_with_work" not in resource_calls
resource_call_counts = (ROOT / "src/proof/replay/resource_call_name_counts.elisa").read_text(encoding="utf-8")
assert "proof_replay_resource_call_name_is_irrelevant_with_work" in resource_call_counts
resource_call_omission = function_body(
    ROOT / "src/proof/replay/resource_call_shadow_validation.elisa",
    "proof_replay_resource_call_name_is_irrelevant_with_work",
)
resource_call_shadow_guard = function_body(
    ROOT / "src/proof/replay/resource_call_shadow_validation.elisa",
    "proof_replay_resource_call_shadow_name_in_statements",
)
assert "parameter.name == wanted" in resource_call_omission
assert "proof_replay_resource_call_shadow_name_in_statements(owner_body, wanted" in resource_call_omission
assert "Ast::Stmt.VarDecl(name, type_expression, initializer, _)" in resource_call_shadow_guard
assert "variable == wanted" in resource_call_shadow_guard
assert "Ast::Stmt.Match(_, _, _) | Ast::Stmt.Invalid:" in resource_call_shadow_guard
resource_call_shadow_expr = function_body(
    ROOT / "src/proof/replay/resource_call_shadow_validation.elisa",
    "proof_replay_resource_call_shadow_name_in_expr",
)
assert "Ast::Expr.Field(_, method, _)" in resource_call_shadow_expr
assert "method == wanted" in resource_call_shadow_expr
assert "Ast::Expr.Scope(_, _, _)" in resource_call_shadow_expr
assert "A dynamic callee has no name-only purity proof." in resource_call_shadow_expr
resource_call_nonfunction_guard = function_body(
    ROOT / "src/proof/replay/resource_call_shadow_validation.elisa",
    "proof_replay_resource_call_nonfunction_name_present",
)
assert "Ast::Decl.Const(name" in resource_call_nonfunction_guard
assert "Ast::Decl.Func(name" in resource_call_nonfunction_guard
assert "proof_replay_resource_call_nonfunction_name_present(report.source.source_declarations" in resource_call_omission
resource_call_counts = function_body(
    ROOT / "src/proof/replay/resource_call_name_counts.elisa",
    "proof_replay_resource_call_name_counts_match",
)
resource_call_opaque_target = function_body(
    resource_source_path, "proof_replay_resource_call_has_opaque_target_with_work"
)
assert "return false if not omission_sources_clear" in resource_call_omission
assert "proof_replay_resource_call_has_opaque_target_with_work" in resource_call_counts
assert "proof_replay_summary_has_unresolved_import" in resource_call_counts
assert "index.source_counts[row] > index.event_counts[row]" in resource_call_counts
assert "Ast::Decl.Extern(_, _, _, _, _, _, _, _) | Ast::Decl.Import(_, _) | Ast::Decl.Invalid" in resource_call_opaque_target
resource_scalar = function_body(
    ROOT / "src/proof/replay/resource_type_source_validation.elisa",
    "proof_replay_resource_scalar_type_with_work",
)
assert "PROOF_REPLAY_AST_DEPTH_LIMIT" in resource_scalar
assert "proof_replay_owner_work_charge(sview_len(name), source_work)" in resource_scalar
assert 'name in {"i8", "i16", "i32", "i64", "isize", "int", "u8", "u16", "u32", "u64", "usize", "uintptr", "bool", "char", "f32", "f64"}' in resource_scalar
assert "proof_resource_type_is_scalar" not in (ROOT / "src/proof/replay/resource_type_source_validation.elisa").read_text(encoding="utf-8")
resource_sview = function_body(
    ROOT / "src/proof/replay/resource_type_source_validation.elisa",
    "proof_replay_resource_sview_type_with_work",
)
assert "PROOF_REPLAY_AST_DEPTH_LIMIT" in resource_sview
assert "proof_replay_thread_import_shadow_check(report, name, owner_path, source_work)" in resource_sview
assert "proof_replay_thread_marker_type_declaration(report, name, source_work, 0)" in resource_sview
assert "declaration.nested_scope or declaration.count > 1" in resource_sview
assert 'if name == "sview":' in resource_sview
assert "declaration.kind != \"alias\" or declaration.has_formals" in resource_sview
assert "proof_replay_resource_sview_type_with_work(declaration.target, report, owner_path, source_work, depth + 1)" in resource_sview
assert "Ast::Expr.Refinement(inner" in resource_sview
assert "proof_resource_type_is_sview" not in (ROOT / "src/proof/replay/resource_type_source_validation.elisa").read_text(encoding="utf-8")
resource_events = function_body(
    ROOT / "src/proof/replay/certificate_validation.elisa",
    "proof_replay_resource_event_facts_with_owner",
)
trace_owner = function_body(
    ROOT / "src/proof/replay/certificate_validation.elisa",
    "proof_replay_trace_owner_matches_consumer_with_work",
)
assert "if owner != consumer_name:" in trace_owner
assert 'if node.kind == "resource-write":' in resource_events
assert "proof_replay_resource_write_source_valid_with_work(report, node" in resource_events
assert "proof_replay_resource_call_site_matches_owner_with_work(report, resource_root, node" in resource_events
assert resource_events.rstrip().endswith("return false")
resource_call_child_checks = function_body(
    ROOT / "src/proof/kernel_replay/arena_child_validation.elisa",
    "proof_kernel_replay_arena_children_valid_with_work",
)
assert 'if node.kind == "resource-call" and index < node.auxiliary:' in resource_call_child_checks
assert 'if node.kind == "resource-call" and index >= node.auxiliary:' in resource_call_child_checks
assert 'if node.kind == "resource-call-lend" and index < node.auxiliary:' in resource_call_child_checks
resource_call_arg_shape = function_body(
    ROOT / "src/proof/kernel_replay/arena_shapes.elisa",
    "proof_kernel_replay_arena_resource_event_shape",
)
assert 'node.kind == "resource-call-arg"' in resource_call_arg_shape
assert "node.children_count == 0" in resource_call_arg_shape
resource_scope_merge = function_body(
    ROOT / "src/proof/resources/state_and_regions.elisa", "proof_resource_close_child"
)
assert "for event in child.evidence.trace_events" in resource_scope_merge
assert '"resource-scope"' in resource_scope_merge
resource_expression_calls = function_body(
    ROOT / "src/proof/resources/expression_checker.elisa",
    "proof_resource_check_expression",
)
assert resource_expression_calls.index("for argument in arguments") < resource_expression_calls.index("proof_resource_record_call(")

attempt_source = function_body(
    ROOT / "src/proof/replay/attempt_fact_source_validation.elisa",
    "proof_replay_attempt_fact_context_source_valid_with_work",
)
assert "proof_replay_trace_owner_source_position_for_attempt_with_work(report, attempt, source_work)" in attempt_source
assert "report.analysis_2.replay_owner_offset <- owner_position.offset.usize()" in attempt_source
assert "report.analysis_2.replay_owner_offset_valid <- true" in attempt_source
assert "report.analysis_2.replay_owner_offset <- saved_owner_offset" in attempt_source

attempt_proven = function_body(checked_view, "proof_checked_view_attempt_is_proven")
for gate in (
    "proof_checked_view_source_validated(view)",
    "proof_checked_view_goal_source_admissible(view, attempt_index)",
    "proof_checked_view_goal_facts_source_admissible(view, attempt_index)",
    "proof_replay_receipt_attempt_is_proven(view.receipt, attempt_index)",
):
    assert gate in attempt_proven, gate

replay_api = ROOT / "src/proof/replay/api.elisa"
receipt_status = ROOT / "src/proof/replay/receipt_status.elisa"
kernel_only = function_body(receipt_status, "proof_replay_receipt_kernel_attempt_status")
assert "not receipt.source_bound" not in kernel_only
assert "Low-trust standalone replay diagnostic" in receipt_status.read_text(encoding="utf-8")
source_proven = function_body(receipt_status, "proof_replay_receipt_attempt_is_proven")
for gate in (
    "receipt.source_bound",
    "receipt.source_validated",
    "not receipt.source_goal_statuses_complete",
    "not receipt.source_attempt_fact_statuses_complete",
    "receipt.source_goal_statuses.count != receipt.attempt_proven_statuses.count",
    "receipt.source_attempt_fact_statuses.count != receipt.attempt_proven_statuses.count",
    "not receipt.source_goal_statuses[attempt_index]",
    "not receipt.source_attempt_fact_statuses[attempt_index]",
    "attempt_index >= receipt.attempt_proven_statuses.count",
):
    assert gate in source_proven, gate
receipt_attempt_status = function_body(receipt_status, "proof_replay_receipt_attempt_status")
assert "not receipt.source_bound or not receipt.source_validated" in receipt_attempt_status
standalone_attempt = function_body(receipt_status, "proof_replay_receipt_kernel_attempt_status")
assert "not receipt.source_bound" not in standalone_attempt
assert "proof_replay_receipt_attempt_is_proven" in receipt_status.read_text(encoding="utf-8")
standalone_replay = function_body(replay_api, "proof_replay_certificates")
assert "proof_replay_receipt_from_report(report, false)" in standalone_replay
receipt_complete = function_body(receipt_status, "proof_replay_receipt_is_complete")
for gate in (
    "receipt.issued",
    "receipt.source_bound",
    "receipt.source_validated",
    "receipt.complete",
    "receipt.theorem_source_admissions.count != receipt.source_theorem_count",
):
    assert gate in receipt_complete, gate
assert visibility_before(replay_api, "proof_replay_receipt_from_report") == "private"
receipt_issuer = function_body(replay_api, "proof_replay_receipt_from_report")
assert "source_validated: bool" in receipt_issuer
checked_transaction = function_body(replay_api, "proof_check_and_replay_with_source")
assert "proof_replay_receipt_from_report(report, false)" in checked_transaction
assert "receipt.source_theorem_count <- report.analysis_1.theorems.summaries.count" in checked_transaction
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
finding_counts = function_body(status_helpers, "proof_output_finding_counts_with_work")
assert "source_admitted_goals" not in finding_counts
assert "proof_checked_view_goal_source_admissible(checked_view, finding.goal_id)" in finding_counts
assert "proof_checked_view_goal_facts_source_admissible(checked_view, finding.goal_id)" in finding_counts
assert "proof_output_reserve_status_snapshot_work(work_used, 2)" in finding_counts
finding_summary = function_body(status_helpers, "proof_output_checked_view_finding_summary_with_work")
assert "source_admitted_goals" not in finding_summary
assert "proof_output_finding_counts_with_work(checked_view, work_used)" in finding_summary
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
    assert 'verdict <- "failed" if verdict == "proved" and (not source_complete or not replay_complete or not effective_source_admissible)' in serializer
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
assert "source_admitted: bool = proof_checked_view_goal_source_admissible(checked_view, goal_id) and proof_checked_view_goal_facts_source_admissible(checked_view, goal_id)" in single_goal_snapshot

explain_output = ROOT / "src/app/explain_output.elisa"
explained_goal = function_body(explain_output, "proof_push_goal_explanation_with_replayed")
assert "producer_claim: bool = goal_status.producer_claimed" in explained_goal
assert 'goal_state_result.state == "proved" and producer_claim and replayed and source_admitted' in explained_goal

# Equality rewriting is unsound for IEEE floats because NaN makes equality nonreflexive.
# Keep rewrite operands and the equality witness float-free, and require integer witnesses for
# substituted expressions. The surrounding goal may contain unrelated opaque float atoms.
tactic_replay = ROOT / "src/proof/kernel_replay/tactic_replay.elisa"
rewrite_transition = tactic_replay.read_text(encoding="utf-8").split('if action == "rewrite":', 1)[1]
transition_work = (ROOT / "src/proof/kernel_replay/tactic_transition_work.elisa").read_text(encoding="utf-8")
assert 'return false if reject_float and node.kind in {"float", "opaque-float-literal"}' in transition_work
assert "proof_kernel_replay_tactic_effect_free_with_work(nodes, children, before_goal, before_facts, 0, step_work, false)" in rewrite_transition
assert "proof_kernel_replay_tactic_effect_free_with_work(nodes, children, argument, before_facts, 0, step_work, true)" in rewrite_transition
assert "proof_kernel_replay_tactic_effect_free_with_work(nodes, children, secondary, before_facts, 0, step_work, true)" in rewrite_transition
assert "proof_kernel_replay_denial_integer_term_with_work(nodes, children, argument, before_facts, step_work, 0)" in rewrite_transition
assert "proof_kernel_replay_denial_integer_term_with_work(nodes, children, secondary, before_facts, step_work, 0)" in rewrite_transition
assert "argument_integer_type == 0 or argument_integer_type != secondary_integer_type" in rewrite_transition

# Proof-text export is an artifact boundary. Keep its `proof` / `qed` marker tied directly
# to replay plus selected-goal and premise source admission, rather than relying on a
# transitive promise about the status helper's current implementation.
proof_output = ROOT / "src/app/proof_output.elisa"
proof_export = function_body(proof_output, "proof_push_elisa_proof_with_replayed")
assert 'goal_verified: bool = goal_state == "proved" and certificate_replayed and goal_source_admissible' in proof_export
assert 'keyword <- "proof" if goal_verified' in proof_export
assert 'if goal_verified:' in proof_export
focused_goal_json = function_body(proof_output, "proof_push_json_focused_goal_with_replayed")
assert 'replay_proven: bool = attempt_status == "proved" and attempt_replayed and goal_source_admissible' in focused_goal_json

# JSON declaration and theorem claims are public proof-admission routes. Keep producer
# `verified` bits as candidates until replay and source correspondence both admit them.
theorem_output = ROOT / "src/app/theorem_output.elisa"
declaration_json = function_body(theorem_output, "proof_push_json_declaration")
assert 'proof_push(buffer, "true" if declaration.verified and source_clean and source_admissions_complete' in declaration_json
for gate in ("declaration_gaps.complete", "declaration_gaps.found", "not replay_gap", "not source_gap"):
    assert gate in declaration_json, gate
theorem_json = function_body(theorem_output, "proof_push_json_theorem")
assert "kernel_verified and source_claim_admissible" in theorem_json
assert "proof_replay_complete: mutable bool = theorem.verified and valid_proof_goals and theorem.proof_goals_count > 0" in theorem_json
assert "theorem_source_admissible and source_admissions_complete and declaration_identity_unambiguous and valid_proof_goals" in theorem_json

# Resource event names are diagnostic labels. Keep each read, move, and write tied to the
# parser-derived active binder, then have kernel replay compare that event root to its live slot.
resource_identity_path = ROOT / "src/proof/replay/resource_binding_identity_validation.elisa"
resource_identity = resource_identity_path.read_text(encoding="utf-8")
resource_owner = function_body(
    ROOT / "src/proof/replay/resource_call_source_validation.elisa",
    "proof_replay_resource_safety_owner_valid_with_work",
)
assert "proof_replay_resource_binding_identities_source_valid_with_work(report, root, parameters, body, source_work)" in resource_owner
resource_identity_pass = function_body(
    resource_identity_path, "proof_replay_resource_binding_identities_source_valid_with_work"
)
assert "proof_replay_resource_binding_position_index_build_with_work(report, root, source_work)" in resource_identity_pass
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
assert 'proof_replay_resource_binding_position_find_with_work(report, index, "resource-bind", position.end_offset.usize(), name' in resource_identity
assert 'proof_replay_resource_binding_event_annotate_with_work(report, index, "resource-write"' in resource_identity
resource_kernel = (ROOT / "src/proof/kernel_replay/resource_events.elisa").read_text(encoding="utf-8")
assert resource_kernel.count("proof_kernel_replay_resource_binding_event_identity_matches(state, nodes, slot, node.auxiliary)") >= 3
resource_identity_kernel = function_body(
    ROOT / "src/proof/kernel_replay/resource_state.elisa",
    "proof_kernel_replay_resource_binding_event_identity_matches",
)
assert 'nodes[root].kind not in {"resource-bind", "resource-region-alloc", "resource-region-bind", "resource-call-result"}' in resource_identity_kernel
assert "nodes[root].name == state.bindings.binding_names[slot]" in resource_identity_kernel

print("source authority guards: receipt boundaries and bounded resource-prefix capabilities remain enforced")
