"""Require every emitted resource event to be validated or explicitly refused at replay."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
producer_call = re.compile(
    r"proof_resource_record_event(?:_at_position)?\(\s*[^,\n]+,\s*[^,\n]+,\s*\"([^\"]+)\""
)
produced = set()
direct_nodes = set()
for source in (ROOT / "src/proof/resources").rglob("*.elisa"):
    text = source.read_text(encoding="utf-8")
    produced.update(producer_call.findall(text))
    direct_nodes.update(re.findall(
        r'proof_kernel_add_node\(&report\.analysis_1\.kernel\.nodes,\s*"(resource-[^"]+)"', text
    ))

expected_produced = {
    "resource-bind",
    "resource-call-result",
    "resource-move",
    "resource-region-alloc",
    "resource-region-alloc-discard",
    "resource-region-assign",
    "resource-region-bind",
    "resource-region-call-alloc",
    "resource-region-close",
    "resource-region-open",
    "resource-region-param",
    "resource-region-rebind-alloc",
    "resource-region-return",
    "resource-region-return-alloc",
    "resource-use",
    "resource-write",
}
assert produced == expected_produced, (produced, expected_produced)

certificate_validation = (ROOT / "src/proof/replay/certificate_validation.elisa").read_text(encoding="utf-8")
start = certificate_validation.index("def proof_replay_resource_event_facts_with_owner")
end = certificate_validation.index("# A certificate may only replay facts", start)
dispatch = certificate_validation[start:end]
handled = set(re.findall(r'node\.kind\s*==\s*"([^"]+)"', dispatch))
for group in re.findall(r'node\.kind\s+in\s+\{([^}]*)\}', dispatch):
    handled.update(re.findall(r'"([^"]+)"', group))

explicitly_refused = {
    "resource-region-call-alloc",
    "resource-region-rebind-alloc",
    "resource-region-bind",
    "resource-join-move",
    "resource-call-result",
}
refusal_groups = re.findall(r'if node\.kind in \{([^}]*)\}:\s*return false', dispatch, re.S)
refusal = next((group for group in refusal_groups if '"resource-region-call-alloc"' in group), "")
assert refusal, "unbridged resource-event refusal boundary is missing"
assert set(re.findall(r'"([^"]+)"', refusal)) == explicitly_refused
assert produced <= handled, (produced - handled, handled)
assert produced - explicitly_refused <= handled
assert 'if node.kind == "resource-call":' in dispatch
assert 'if node.kind == "resource-call-lend":' in dispatch
assert "proof_replay_resource_call_site_matches_owner_with_work(report, resource_root, node, active_owner" in dispatch
assert 'if node.kind in {"resource-safety", "resource-scope", "resource-alternatives"}:' in dispatch
assert 'if node.kind == "resource-disjoint":' in dispatch
assert 'proof_replay_resource_owner_prefix_event_valid_with_work(report, resource_root, root, active_resource_prefix_end' in dispatch
assert '"resource-join-move"' in refusal
assert '"resource-call-result"' in refusal

# Direct resource nodes are broader than the trace leaves above: they also include
# container roots and call payload children. Pin the whole producer surface and
# require those payloads to flow through the source-bound call-site validator.
expected_direct_nodes = {
    "resource-alternatives", "resource-call", "resource-call-arg", "resource-call-formal",
    "resource-call-region", "resource-call-lend", "resource-call-result", "resource-disjoint",
    "resource-join-move", "resource-region-bind", "resource-region-return", "resource-safety",
    "resource-scope", "resource-sview-param",
}
assert direct_nodes == expected_direct_nodes, (direct_nodes, expected_direct_nodes)
call_validation = (ROOT / "src/proof/replay/resource_call_source_validation.elisa").read_text(encoding="utf-8")
event_validation = (ROOT / "src/proof/replay/resource_event_source_validation.elisa").read_text(encoding="utf-8")
assert "proof_replay_resource_call_site_matches_owner_with_work" in call_validation
assert 'event.kind != "resource-call" and event.kind != "resource-call-lend"' in call_validation
argument_matcher = call_validation.split("def proof_replay_resource_call_arguments_match_with_work", 1)[1].split(
    "# Check prefix-node aliasing", 1
)[0]
for required in (
    'argument.kind != "resource-call-arg"',
    'argument.name != parameters[argument_index].name',
    "proof_replay_ast_matches_kernel_with_work(report, source_argument, argument.left, source_work, 0)",
    'formal.kind != "resource-call-formal"',
    'region.kind != "resource-call-region"',
    'linked_summary.kind != "resource-safety"',
    "linked_summary.value != position.offset.i64()",
):
    assert required in argument_matcher + call_validation, required
for nested in {"resource-call-arg", "resource-call-formal", "resource-call-region"}:
    assert f'"{nested}"' in call_validation, nested
for container in {"resource-safety", "resource-scope", "resource-alternatives"}:
    assert f'"{container}"' in call_validation + event_validation, container
assert '"resource-disjoint"' in call_validation + event_validation

print("resource event source boundary: trace leaves and direct resource nodes are inventoried and classified")
