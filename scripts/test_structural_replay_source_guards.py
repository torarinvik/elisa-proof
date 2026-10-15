"""Keep structural-safety replay bound to independently rebuilt source evidence."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "src/proof/replay/api.elisa").read_text(encoding="utf-8")
replay_entry = (ROOT / "src/proof/replay.elisa").read_text(encoding="utf-8")
replay = (ROOT / "src/proof/replay/structural_source_cache_validation.elisa").read_text(encoding="utf-8")
source_graph = (ROOT / "src/proof/replay/structural_source_validation.elisa").read_text(encoding="utf-8")
call_sites = (ROOT / "src/proof/replay/structural_call_site_index.elisa").read_text(encoding="utf-8")
call_coverage = (ROOT / "src/proof/replay/source_call_coverage.elisa").read_text(encoding="utf-8")
trace_validation = (ROOT / "src/proof/replay/fact_trace_validation.elisa").read_text(encoding="utf-8")
generic_lookup = (ROOT / "src/proof/check/source_conversion_name_lookups.elisa").read_text(encoding="utf-8")
replay_generic_lookup = (ROOT / "src/proof/replay/source_generic_parameter_index.elisa").read_text(encoding="utf-8")
implicit_effect = (ROOT / "src/proof/check/implicit_effect_guard.elisa").read_text(encoding="utf-8")
operator_guard = (ROOT / "src/proof/check/structural_operator_guard.elisa").read_text(encoding="utf-8")
purity_index = (ROOT / "src/proof/check/purity_and_function_index.elisa").read_text(encoding="utf-8")
extern_effect = (ROOT / "src/proof/check/extern_contract_effect_index.elisa").read_text(encoding="utf-8")

# Threaded-summary marker types and depth bounds are factored into a helper module; its
# declaration must precede both syntax reconstruction and the summary checker that use it.
assert replay_entry.index('include "./replay/threaded_summary_type_markers.elisa"') < replay_entry.index('include "./replay/threaded_type_markers.elisa"')
assert replay_entry.index('include "./replay/threaded_type_markers.elisa"') < replay_entry.index('include "./replay/threaded_summaries.elisa"')
threaded_marker_types = (ROOT / "src/proof/replay/threaded_summary_type_markers.elisa").read_text(encoding="utf-8")
assert "struct ProofReplayThreading:" in threaded_marker_types
assert "const PROOF_REPLAY_THREAD_DEPTH_LIMIT: usize = 96" in threaded_marker_types

# Generic owner checks use exact declaration identity whenever the caller owns the
# declaration. Their line-only compatibility path is available only to ownerless callers.
generic_owner_lookup = generic_lookup.split("def proof_source_conversion_generic_name(", 1)[1].split(
    "def proof_source_conversion_scope_root_name(", 1
)[0]
assert "report.context.current_goal_owner_offset.usize()" in generic_owner_lookup
assert "return (false, 0) if owner_known" in generic_owner_lookup
assert "proof_source_conversion_generic_name(name, declaration_line, report, caller_owner_known)" in implicit_effect
assert "proof_source_conversion_generic_name(concrete.name, declaration_line, report, caller_owner_known)" in operator_guard
generic_replay_owner_lookup = replay_generic_lookup.split("def proof_replay_call_generic_param_name(", 1)[1].split(
    "def ", 1
)[0]
assert "field_conversion_generic_param_owner_known and not call_target.generics.field_conversion_generic_param_owner_offset_valid" in generic_replay_owner_lookup
assert "generic_owner_line != call_target.generics.field_conversion_generic_param_line" in generic_replay_owner_lookup
assert "report.context.current_goal_owner_offset <- functions.lookup.offsets[function_index]" in purity_index
assert "report.context.current_goal_owner_offset <- functions.lookup.offsets[function_index]" in extern_effect

source_index_build = source_graph.split("def proof_replay_structural_source_index_build(", 1)[1].split(
    "def proof_replay_structural_source_lookup(", 1
)[0]
assert "proof_replay_structural_collect_source_entries(declarations" in source_index_build
assert "proof_replay_structural_import_annotation_unresolved(annotation" in source_index_build

certificate_check = replay.split("def proof_replay_structural_certificate_source_valid_with_work(", 1)[1]
for requirement in (
    "root.secondary_name != \"structural-v2\"",
    "proof_replay_structural_call_site_matches(cache.graph, caller_node, root.left, edge.secondary_name, certificate.line, source_work)",
    "proof_replay_structural_graph_has_edge(cache.graph, caller_node, callee_node, source_work)",
    "cache.graph.nodes.component_ids[caller_node] != cache.graph.nodes.component_ids[callee_node]",
    "proof_check_structural_function(cache.enum_index, certificate.name, position.line, parameters, body",
    "proof_replay_structural_certificate_set_matches_with_work(report, cache.certificate_index, certificate.name, cache.scratch, source_work)",
):
    assert requirement in certificate_check, requirement
certificate_set_check = certificate_check.index("proof_replay_structural_certificate_set_matches_with_work(report, cache.certificate_index, certificate.name, cache.scratch, source_work)")
memo_write = certificate_check.index("cache.certificate_index.owners[certificate_owner.owner_index].source_validated <- true")
assert certificate_set_check < memo_write
assert "source_validated: false" in (ROOT / "src/proof/replay/structural_certificate_index.elisa").read_text(encoding="utf-8")
assert "proof_replay_structural_certificate_source_valid_with_work(report, certificate" in trace_validation
assert 'if certificate.rule == "structural-safety":' in trace_validation
assert "return (ElisaProofKernelReplay::proof_kernel_validate_structural_witness_shape_with_workspace" in trace_validation
assert "can[Global{Read,Write}])" in trace_validation

# The source-validation cache contains a `source_validated` memo. Keep its
# authority within one synchronous replay of the unchanged report.
batch_replay = api.split("def proof_replay_certificates_mutating[@r](", 1)[1].split(
    "public:", 1
)[0]
cache_declaration = "structural_cache: mutable ProofReplayStructuralValidationCache = ProofReplayStructuralValidationCache{}"
assert batch_replay.index("certificate.replayed <- false") < batch_replay.index(cache_declaration)
assert "proof_replay_certificate_with_cache(report, report.analysis_1.certificates[index], index, validation_workspace, structural_cache)" in batch_replay
assert batch_replay.index("validation_workspace.allow_replayed_dependency_memo <- true") < batch_replay.index(
    "for index in 0..<report.analysis_1.certificates.count"
)
assert batch_replay.index("validation_workspace.allow_replayed_dependency_memo <- false") < batch_replay.index(
    "proof_replay_certificates_complete_with_work"
)
call_walk = call_coverage.split("def proof_replay_call_expression_with_index(", 1)[1].split(
    "def proof_replay_call_body(", 1
)[0]
assert "Ast::Expr.Call(callee, arguments, argument_names, position)" in call_walk
assert "for bound in bindings |bound, name, shadowed, work|" in call_walk
assert "call_target.selection.unresolved_dispatch_found <- true" in call_walk
assert "Ast::Stmt.VarDecl(name, type_expression, value, _)" in call_coverage
assert "bindings.push(name)" in call_coverage

call_site_match = call_sites.split("def proof_replay_structural_call_site_matches(", 1)[1]
for requirement in (
    "not graph.call_sites.call_site_scan_valid[caller]",
    "graph.call_sites.call_site_scoped[row]",
    "graph.call_sites.call_site_counts[row] != 1",
    "graph.call_sites.call_site_lines[row] != line",
    "graph.call_sites.call_site_names[row] == name",
):
    assert requirement in call_site_match, requirement

fixtures = (ROOT / "scripts/tests/fixtures/structural_replay_mutations.elisa").read_text(encoding="utf-8")
indirect_fixture = (ROOT / "examples/rejected_structural_local_function_value.elisa").read_text(encoding="utf-8")
structural_e2e = (ROOT / "scripts/test_adt_library.py").read_text(encoding="utf-8")
structural_shell = (ROOT / "scripts/test.d/04-borrows-and-statuses.sh").read_text(encoding="utf-8")
assert "callback: fn(LocalCallbackNat) -> i64 = local_callback_bounce" in indirect_fixture
assert "callback(n)" in indirect_fixture
assert 'run("rejected_structural_local_function_value.elisa")' in structural_e2e
assert 'captured_structural_accumulator.elisa' in structural_shell
for requirement in (
    'data["summary"]["semantic_errors"] == 0',
    'data["replay"]["gaps"] == 0',
    'data["trust"]["trusted_assumptions"] == []',
    'f["kind"] == "structural-decreases-unproven"',
    'f["name"] == "local_callback_bounce"',
):
    assert requirement in structural_e2e, requirement
api_test = (ROOT / "scripts/test_direct_api_semantic_admission.py").read_text(encoding="utf-8")
for mutation in (
    "api_structural_certificate_offset_tamper",
    "api_structural_certificate_callee_tamper",
    "api_structural_certificate_subject_tamper",
    "api_structural_certificate_binder_tamper",
    "api_structural_certificate_omission",
    "api_structural_ambiguous_owner_source",
    "api_structural_ambiguous_callee_source",
    "api_structural_import_declaration_tamper",
    "api_structural_import_annotation_tamper",
):
    assert f"def {mutation}(" in fixtures
    assert mutation in api_test

print("structural replay guards: source graph, call-site identity, witness shape, and mutation routes stay linked")
