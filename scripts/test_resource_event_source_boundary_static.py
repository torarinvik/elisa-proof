"""Require every emitted resource event to be validated or explicitly refused at replay."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(source: str, name: str) -> str:
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"missing function {name}")


producer_call = re.compile(
    r"proof_resource_record_event(?:_at_position)?\(\s*[^,\n]+,\s*[^,\n]+,\s*\"([^\"]+)\""
)
produced = set()
positioned_produced = set()
direct_nodes = set()
for source in (ROOT / "src/proof/resources").rglob("*.elisa"):
    text = source.read_text(encoding="utf-8")
    produced.update(producer_call.findall(text))
    positioned_produced.update(re.findall(
        r'proof_resource_record_event_at_position\(\s*[^,\n]+,\s*[^,\n]+,\s*"([^"]+)"', text
    ))
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
    "resource-region-bind",
    "resource-call-result",
}
refusal_groups = re.findall(r'if node\.kind in \{([^}]*)\}:\s*return false', dispatch, re.S)
refusal = next((group for group in refusal_groups if '"resource-region-bind"' in group), "")
assert refusal, "unbridged resource-event refusal boundary is missing"
assert set(re.findall(r'"([^"]+)"', refusal)) == explicitly_refused
assert produced <= handled, (produced - handled, handled)
assert produced - explicitly_refused <= handled
assert 'if node.kind == "resource-region-call-alloc":' in dispatch
assert "proof_replay_resource_call_allocation_source_valid_with_work(report, resource_root, root, node" in dispatch
for helper in (
    "proof_replay_resource_region_alloc_source_valid_with_work",
    "proof_replay_resource_region_rebind_alloc_source_valid_with_work",
):
    assert re.search(rf"{helper}\([^\n]*\) can Global\{{Read,Write\}}", dispatch), helper
assert 'if node.kind == "resource-call":' in dispatch
assert 'if node.kind == "resource-call-lend":' in dispatch
assert "proof_replay_resource_call_site_matches_owner_with_work(report, resource_root, node, active_owner" in dispatch
assert 'if node.kind in {"resource-safety", "resource-scope", "resource-alternatives"}:' in dispatch
assert 'if node.kind == "resource-disjoint":' in dispatch
assert 'proof_replay_resource_owner_prefix_event_valid_with_work(report, resource_root, root, active_resource_prefix_end' in dispatch
assert 'if node.kind == "resource-alternatives":' in dispatch
assert "proof_replay_resource_alternatives_source_valid_with_work(report, root, node, active_owner" in dispatch
assert 'if node.kind == "resource-join-move":' in dispatch
assert '"resource-join-move"' not in refusal
assert '"resource-call-result"' in refusal

alternative_source = (ROOT / "src/proof/replay/resource_alternative_source_validation.elisa").read_text(encoding="utf-8")
alternative_scope = function_body(alternative_source, "proof_replay_resource_alt_scope_has_source")
assert 'if node.kind == "resource-safety" or node.kind == "resource-disjoint":' in alternative_scope
assert 'if node.kind == "resource-join-move":' in alternative_scope
assert "proof_replay_owner_work_charge(1, work)" in alternative_source
assert "matches == 1" in function_body(alternative_source, "proof_replay_resource_alternatives_source_valid_with_work")
alternative_bind = function_body(alternative_source, "proof_replay_resource_alt_bind_matches")
assert '"resource-bind-inventory", node.name' in alternative_bind
assert '"resource-bind-loop-inventory", node.name' in alternative_bind
event_validation = (ROOT / "src/proof/replay/resource_event_source_validation.elisa").read_text(encoding="utf-8")
resource_state = (ROOT / "src/proof/resources/state_and_regions.elisa").read_text(encoding="utf-8")
event_find_statements = function_body(event_validation, "proof_replay_resource_event_find_statements_with_work")
assert "Ast::Stmt.Return(expression, _) | Ast::Stmt.Contract(_, expression, _):" in event_find_statements
assert "expression is not Ast::Expr.Absent and not proof_replay_resource_event_find_expression_with_work(expression," in event_find_statements
assignment_coverage = function_body(
    event_validation, "proof_replay_resource_region_assignment_statements_covered_with_work"
)
assert "Ast::Stmt.Return(expression, _) | Ast::Stmt.Contract(_, expression, _):" in assignment_coverage
assert "expression is not Ast::Expr.Absent and not proof_replay_resource_region_assignment_expression_blocks_covered_with_work(report, root, prefix_end, expression," in assignment_coverage
positioned_bind_producer = function_body(resource_state, "proof_resource_add_binding_traced_at_position")
assert "position.end_offset.i64()" in positioned_bind_producer
bind_source = function_body(event_validation, "proof_replay_resource_event_find_statements_with_work")
assert 'position.end_offset == offset.u32()' in bind_source
assert 'iterable_position.end_offset == offset.u32()' in bind_source

resource_summary_shape = function_body(
    (ROOT / "src/proof/kernel_replay/arena_shapes.elisa").read_text(encoding="utf-8"),
    "proof_kernel_replay_arena_resource_summary_shape",
)
assert 'node.kind == "resource-alternatives"' in resource_summary_shape
assert "node.value >= 0 and node.value <= 4294967295" in resource_summary_shape

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
call_site_validation = (ROOT / "src/proof/replay/resource_call_site_validation.elisa").read_text(encoding="utf-8")
resource_ordering = (ROOT / "src/proof/replay/resource_trace_order_validation.elisa").read_text(encoding="utf-8")
ordered_events = function_body(resource_ordering, "proof_replay_resource_event_offsets_ordered_with_work")
positioned_events = ordered_events.split("positioned: bool =", 1)[1].split("\n            if positioned:", 1)[0]
ordered_positioned_kinds = set(re.findall(r'"([^"]+)"', positioned_events))
assert positioned_produced <= ordered_positioned_kinds, (positioned_produced - ordered_positioned_kinds)
assert 'if node.kind == "resource-region-alloc":' in ordered_events
assert '"resource-region-alloc-inventory", node.name, allocation_matches, allocation_initializer' in ordered_events
assert "proof_replay_resource_return_expr_end_with_work(allocation_initializer, source_work, 0, &allocation_end)" in ordered_events
assert "current_offset <- allocation_end" in ordered_events
assert 'if node.kind == "resource-region-alloc-discard":' in ordered_events
assert 'body, current_offset, node.kind, node.secondary_name, discarded_matches, discarded_allocation' in ordered_events
assert "proof_replay_resource_return_expr_end_with_work(discarded_allocation, source_work, 0, &discarded_end)" in ordered_events
assert "current_offset <- discarded_end" in ordered_events
region_alloc_source = (ROOT / "src/proof/replay/resource_region_alloc_source_validation.elisa").read_text(encoding="utf-8")
region_alloc_validator = function_body(region_alloc_source, "proof_replay_resource_region_alloc_source_valid_with_work")
assert 'event.value <= 0 or event.value > 4294967295' in region_alloc_validator
allocation_source = call_site_validation.split("def proof_replay_resource_call_allocation_source_valid_with_work", 1)[1].split(
    "def proof_replay_resource_call_site_matches_owner_with_work", 1
)[0]
assert "allocation.kind != event.kind or allocation.left != event.left or allocation.secondary_name != event.secondary_name" in allocation_source
allocation_index_walk = function_body(
    call_site_validation, "proof_replay_resource_call_allocation_index_walk_with_work"
)
allocation_index_ensure = function_body(
    call_site_validation, "proof_replay_resource_call_allocation_index_ensure_with_work"
)
assert 'is_call: mutable bool = node.kind == "resource-call"' in allocation_index_walk
assert 'is_call <- node.kind == "resource-call-lend"' in allocation_index_walk
assert 'argument.kind != "resource-call-arg" or argument.operator != "region-new"' in allocation_index_walk
assert "parents[allocation_root] <- root" in allocation_index_walk
assert "owners[allocation_root] <- resource_root" in allocation_index_walk
assert "present[allocation_root]" in allocation_index_walk
assert "present[allocation_root] <- true" in allocation_index_walk
assert "proof_replay_owner_work_charge(1, source_work)" in allocation_index_walk
assert "resource_call_allocation_index_attempted" in allocation_index_ensure
assert "resource_call_allocation_index_complete" in allocation_index_ensure
assert "resource_call_allocation_index_node_count" in allocation_index_ensure
assert "node_count < cached_node_count" in allocation_index_ensure
assert "resource_call_allocation_parent_by_node.resize(node_count)" in allocation_index_ensure
assert "resource_call_allocation_owner_by_node.resize(node_count)" in allocation_index_ensure
assert "resource_call_allocation_present_by_node.resize(node_count)" in allocation_index_ensure
assert "proof_replay_owner_work_charge(new_count, source_work)" in allocation_index_ensure
assert "for node_index in indexed_count..<node_count" in allocation_index_ensure
assert 'node.kind != "resource-safety"' in allocation_index_ensure
assert "proof_replay_resource_call_allocation_index_walk_with_work" in allocation_index_ensure
assert "proof_replay_resource_call_allocation_index_ensure_with_work(report, source_work, cache)" in allocation_source
assert "cache.resource_call_allocation_owner_by_node[allocation_root] != resource_root" in allocation_source
assert "not cache.resource_call_allocation_present_by_node[allocation_root]" in allocation_source
assert "parent_root >= report.analysis_1.kernel.nodes.count" in allocation_source
assert "proof_replay_resource_call_site_matches_owner_with_work(report, resource_root, parent" in allocation_source
assert "proof_replay_resource_call_site_matches_owner_with_work" in call_site_validation
assert 'event.kind != "resource-call" and event.kind != "resource-call-lend"' in call_site_validation
resource_expression_checker = (ROOT / "src/proof/resources/expression_checker.elisa").read_text(encoding="utf-8")
resource_call_lending = (ROOT / "src/proof/resources/call_region_lending.elisa").read_text(encoding="utf-8")
resource_ordering = (ROOT / "src/proof/replay/resource_trace_order_validation.elisa").read_text(encoding="utf-8")
resource_shapes = (ROOT / "src/proof/kernel_replay/arena_shapes.elisa").read_text(encoding="utf-8")
assert "new_parts.region, Ast::expr_pos(argument), function_name" in resource_expression_checker
allocation_producer = function_body(resource_call_lending, "proof_resource_add_region_call_allocation")
assert "proof_replay_resource_return_expr_end_with_work(operand" in allocation_producer
assert "allocation_end > 4294967295" in allocation_producer
assert "state.evidence.trace_events.count == trace_event_count + 1" in allocation_producer
assert "state.evidence.trace_events[trace_event_count]" in allocation_producer
assert '"resource-region-call-alloc"' in function_body(resource_ordering, "proof_replay_resource_event_offsets_ordered_with_work")
assert "node.value > 0 and node.value <= 4294967295" in function_body(resource_shapes, "proof_kernel_replay_arena_resource_region_call_alloc_shape")
allocation_source = function_body(
    call_site_validation, "proof_replay_resource_call_allocation_source_valid_with_work"
)
assert "cache.resource_call_allocation_parent_by_node[allocation_root]" in allocation_source
assert "cache.resource_call_allocation_owner_by_node[allocation_root] != resource_root" in allocation_source
assert "proof_replay_resource_call_site_matches_owner_with_work(report, resource_root, parent" in allocation_source
argument_matcher = call_validation.split("def proof_replay_resource_call_arguments_match_with_work", 1)[1].split(
    "# Check prefix-node aliasing", 1
)[0]
for required in (
    'argument.kind != "resource-call-arg"',
    'argument.name != parameters[argument_index].name',
    "proof_replay_ast_matches_kernel_with_work(report, source_argument, argument.left, source_work, 0)",
    'formal.kind != "resource-call-formal"',
    'region.kind != "resource-call-region"',
    'allocation.kind != "resource-region-call-alloc" or allocation.secondary_name != region or allocation.left >= report.analysis_1.kernel.nodes.count',
    "proof_replay_ast_matches_kernel_with_work(report, operand, allocation.left, source_work, 0)",
    'linked_summary.kind != "resource-safety"',
    "linked_summary.value != position.offset.i64()",
    "Ast::Expr.RegionNew(operand, region, position)",
    'allocation.kind != "resource-region-call-alloc" or allocation.secondary_name != region',
    "position.end_offset <= position.offset or not allocation_end_known or allocation.value != allocation_end.i64()",
    "proof_replay_ast_matches_kernel_with_work(report, operand, allocation.left, source_work, 0)",
):
    assert required in argument_matcher + call_validation + call_site_validation, required
for nested in {"resource-call-arg", "resource-call-formal", "resource-call-region"}:
    assert f'"{nested}"' in call_validation, nested
for container in {"resource-safety", "resource-scope", "resource-alternatives"}:
    assert f'"{container}"' in call_validation + event_validation, container
resource_event_facts = function_body(certificate_validation, "proof_replay_resource_event_facts_with_owner")
assert 'if node.kind == "resource-disjoint":' in resource_event_facts
assert "proof_replay_kernel_fact_root_is_traced_with_stack(report, fact, active_owner, dependency_stack, false, true" in resource_event_facts

# The call-event census intentionally stops at a call node. Producer shape guarantees
# nested evaluations are separate owner trace events, while call children are only
# serialized argument/formal/region payloads. Pin both halves so future producer changes
# cannot make a nested resource transition invisible to the owner inventory.
resource_root_producer = function_body(
    (ROOT / "src/proof/resources/state_finish.elisa").read_text(encoding="utf-8"),
    "proof_resource_finish",
)
assert "for event in state.evidence.trace_events" in resource_root_producer
assert "report.analysis_1.kernel.children.push(event)" in resource_root_producer
assert "state.evidence.trace_events.count, function_name" in resource_root_producer
assert '"resource-safety", "resource-v2"' in resource_root_producer

ordinary_call_producer = function_body(resource_call_lending, "proof_resource_record_call")
lend_call_producer = function_body(
    (ROOT / "src/proof/resources/borrows_and_bindings.elisa").read_text(encoding="utf-8"),
    "proof_resource_record_lend_call",
)
for call_producer in (ordinary_call_producer, lend_call_producer):
    assert '"resource-call-arg"' in call_producer
    assert '"resource-call-region"' in call_producer
    assert "state.evidence.trace_events.push(event)" in call_producer
assert '"resource-call-formal"' not in ordinary_call_producer
assert '"resource-call-formal"' in lend_call_producer
assert "start, mapped.count + formal_regions.count" in ordinary_call_producer
assert "start, mapped.count * 2 + lend_formal_regions.count" in lend_call_producer

call_name_walk = function_body(
    (ROOT / "src/proof/replay/resource_call_name_counts.elisa").read_text(encoding="utf-8"),
    "proof_replay_resource_call_names_at_with_work",
)
assert "names.push(node.name)" in call_name_walk
assert "offsets.push(node.value.usize())" in call_name_walk
assert "return true" in call_name_walk.split("if is_event:", 1)[1].split("is_container:", 1)[0]

print("resource event source boundary: trace leaves and direct resource nodes are inventoried and classified")
