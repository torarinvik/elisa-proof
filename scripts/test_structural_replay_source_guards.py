"""Keep structural-safety replay bound to independently rebuilt source evidence."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
replay = (ROOT / "src/proof/replay/structural_source_cache_validation.elisa").read_text(encoding="utf-8")
source_graph = (ROOT / "src/proof/replay/structural_source_validation.elisa").read_text(encoding="utf-8")
call_sites = (ROOT / "src/proof/replay/structural_call_site_index.elisa").read_text(encoding="utf-8")
trace_validation = (ROOT / "src/proof/replay/fact_trace_validation.elisa").read_text(encoding="utf-8")

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
assert "proof_replay_structural_certificate_source_valid_with_work(report, certificate" in trace_validation
assert 'if certificate.rule == "structural-safety":' in trace_validation
assert "return ElisaProofKernelReplay::proof_kernel_validate_structural_witness_shape_with_workspace" in trace_validation

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
