"""Keep active comparison transport on the shared kernel goal-search budget."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/kernel_replay/index_read_equalities.elisa").read_text(encoding="utf-8")
lines = source.splitlines()
start = next(i for i, line in enumerate(lines) if re.match(r"\s*def proof_kernel_replay_comparison_transport\b", line))
indent = len(lines[start]) - len(lines[start].lstrip())
body = []
for line in lines[start + 1 :]:
    if line.strip() and len(line) - len(line.lstrip()) <= indent:
        break
    body.append(line)
body_text = "\n".join(body)

typed_start = next(i for i, line in enumerate(lines) if re.match(r"\s*def proof_kernel_replay_typed_index_read_equality_with_work\b", line))
typed_indent = len(lines[typed_start]) - len(lines[typed_start].lstrip())
typed_body = []
for line in lines[typed_start + 1 :]:
    if line.strip() and len(line) - len(line.lstrip()) <= typed_indent:
        break
    typed_body.append(line)
typed_body_text = "\n".join(typed_body)

# The rule itself stays fail-closed until its arena carries authenticated receiver typing.
# This budget guard covers the separate, active comparison-transport rule in the same file.
assert "proof_kernel_replay_primitive_comparison(" not in body_text
assert body_text.count("proof_kernel_replay_witness_marker_cache_fill_with_work(") == 1
assert body_text.count("proof_kernel_replay_primitive_comparison_with_markers_with_work(") == 2
assert body_text.count("work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT") >= 2
assert "work_used, PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in body_text
assert "proof_kernel_replay_goal_search_charge(work_used)" in body_text

# A typed equality graph may use only source-admitted primitive equality edges; matching
# operand sorts alone does not establish that overloaded `==` is the builtin relation.
assert "proof_kernel_replay_witness_marker_cache_fill_with_work(nodes, children, facts, &markers" in typed_body_text
primitive_check = "proof_kernel_replay_primitive_comparison_with_markers_with_work(nodes, children, markers, candidate.left, candidate.right"
assert typed_body_text.count(primitive_check) == 1
assert typed_body_text.index(primitive_check) < typed_body_text.index("while cursor < reachable.count")
assert "edge_primitive_states.push(1 if primitive else 2)" in typed_body_text
assert "continue if edge_primitive_states[fact_index] != 1" in typed_body_text

# Optional expression-index setup must leave a shared-meter path for an ordered exact hit.
# In particular, the recursive hash walk (including node text) must stop at its setup ceiling,
# and an incomplete/disabled index must not suppress the exact scan.
interval_index = (ROOT / "src/proof/kernel_replay/interval_expression_index.elisa").read_text(encoding="utf-8")
interval_lookup = (ROOT / "src/proof/kernel_replay/goal_metered_interval.elisa").read_text(encoding="utf-8")
equality_source = (ROOT / "src/proof/kernel_replay/difference_constraints.elisa").read_text(encoding="utf-8")


def function_body(text, name):
    source_lines = text.splitlines()
    start = next(i for i, line in enumerate(source_lines) if re.match(rf"\s*def {re.escape(name)}\b", line))
    function_indent = len(source_lines[start]) - len(source_lines[start].lstrip())
    body = []
    for line in source_lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= function_indent:
            break
        body.append(line)
    return "\n".join(body)


def hash_branch(text, marker):
    branch_lines = text.splitlines()
    start = next(i for i, line in enumerate(branch_lines) if marker in line and line.strip().endswith(":"))
    branch_indent = len(branch_lines[start]) - len(branch_lines[start].lstrip())
    end = start + 1
    while end < len(branch_lines):
        line = branch_lines[end]
        if line.strip() and len(line) - len(line.lstrip()) == branch_indent and (line.lstrip().startswith("elif ") or line.lstrip() == "else:"):
            break
        end += 1
    return "\n".join(branch_lines[start:end])


hash_node = function_body(interval_index, "proof_kernel_replay_interval_expr_hash_node")
pair_nodes_valid = function_body(equality_source, "proof_kernel_replay_expr_pair_nodes_valid")
leaf_equal = function_body(equality_source, "proof_kernel_replay_expr_leaf_equal")
enqueue_children = function_body(equality_source, "proof_kernel_replay_expr_pair_enqueue_children")
# Any constructor equality can omit a bound only if the hash preserves its equality class.
# Keep the leaf partition and recursive child partition synchronized across both walkers.
for kind_group in (
    '"absent"',
    '"int" | "bool"',
    '"typed-int"',
    '"float" | "opaque-float-literal" | "string" | "char" | "ident" | "shorthand"',
):
    assert kind_group in leaf_equal
for hash_group in (
    'node.kind == "absent"',
    'node.kind == "int" or node.kind == "bool"',
    'node.kind == "typed-int"',
    '{"float", "opaque-float-literal", "string", "char", "ident", "shorthand"}',
    '{"field", "scope", "call_arg", "field-init"}',
    'node.kind == "unary" or node.kind == "move"',
    'node.kind == "binary" or node.kind == "index" or node.kind == "dict_entry"',
    'node.kind == "slice" or node.kind == "if"',
    '{"array", "tuple", "set", "dict"}',
    '{"index-n", "construct", "record-update"}',
    'node.kind == "call"',
    'node.kind == "quantifier"',
):
    assert hash_group in hash_node, hash_group
for equality_group in (
    '"absent"',
    '"int" | "bool"',
    '"typed-int"',
    '"float" | "opaque-float-literal" | "string" | "char" | "ident" | "shorthand"',
    '"field" | "scope" | "call_arg" | "field-init" | "unary" | "move"',
    '"binary" | "index" | "dict_entry"',
    '"slice" | "if"',
    '"index-n" | "call" | "array" | "tuple" | "set" | "dict" | "construct" | "record-update"',
    '"quantifier"',
):
    assert equality_group in leaf_equal + enqueue_children or equality_group in pair_nodes_valid
hash_kinds = set(re.findall(r'node\.kind == "([^"]+)"', hash_node))
for group in re.findall(r'node\.kind in \{([^}]+)\}', hash_node):
    hash_kinds.update(re.findall(r'"([^"]+)"', group))
equality_kinds = set(re.findall(r'"([^"]+)"', leaf_equal + enqueue_children))
assert equality_kinds == hash_kinds, (sorted(equality_kinds), sorted(hash_kinds))
assert "left.kind != right.kind or left.operator != right.operator" in pair_nodes_valid
assert 'proof_kernel_replay_name_hash(node.kind).i64()' in hash_node
assert 'proof_kernel_replay_name_hash(node.operator).i64()' in hash_node
payloads = {
    'node.kind == "int" or node.kind == "bool"': ("node.value",),
    'node.kind == "typed-int"': ("node.value", "node.name"),
    'node.kind in {"float", "opaque-float-literal", "string", "char", "ident", "shorthand"}': ("node.name",),
    'node.kind in {"field", "scope", "call_arg", "field-init"}': ("node.name", "node.left"),
    'node.kind == "unary" or node.kind == "move"': ("node.left",),
    'node.kind == "binary" or node.kind == "index" or node.kind == "dict_entry"': ("node.left", "node.right"),
    'node.kind == "slice" or node.kind == "if"': ("node.left", "node.right", "node.auxiliary"),
    'node.kind in {"array", "tuple", "set", "dict"}': ("node.children_count", "node.children_start", "node.children_count"),
    'node.kind in {"index-n", "construct", "record-update"}': ("node.children_count", "node.left", "node.children_start"),
    'node.kind == "call"': ("node.auxiliary", "node.children_count", "node.left", "node.children_start"),
    'node.kind == "quantifier"': ("node.name", "node.secondary_name", "node.left", "node.right"),
}
for marker, fields in payloads.items():
    branch = hash_branch(hash_node, marker)
    assert all(field in branch for field in fields), (marker, fields)

bound_lookup = function_body(interval_index, "proof_kernel_replay_interval_bound_for_term_with_work")
assert bound_lookup.index("if bound.term_root == root:") < bound_lookup.index("proof_kernel_replay_interval_expr_index_build(")
assert "                        return bound" in bound_lookup
assert bound_lookup.index("for bound in bounds") < bound_lookup.index("proof_kernel_replay_interval_expr_index_build(")
assert "continuation_reserve: usize = 0" in bound_lookup
assert "setup_allowance: mutable usize = remaining_at_entry / 2" in interval_index
assert "setup_allowance <- available_for_setup if setup_allowance > available_for_setup" in interval_index
assert "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in bound_lookup
assert "skip_expression_scan <- true if cached_state == 4" in bound_lookup
assert "skip_expression_scan <- index.lookup_complete" in bound_lookup
assert "if not skip_expression_scan and not index.build_attempted:" in bound_lookup
assert bound_lookup.index("proof_kernel_replay_interval_expr_cache_scan_miss(root, index, work_used)") > bound_lookup.index("for bound in bounds")
assert bound_lookup.index("proof_kernel_replay_loop_range_atom_key_with_goal_work(nodes, children, root, work_used)") > bound_lookup.index("skip_expression_scan <- true if cached_state == 4")
cache_miss = function_body(interval_index, "proof_kernel_replay_interval_expr_cache_scan_miss")
assert "work >= PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in cache_miss
assert cache_miss.index("proof_kernel_replay_goal_search_charge(work)") < cache_miss.index("index.states[root] <- 4")
builder_start = interval_index.index("def proof_kernel_replay_interval_expr_index_build(")
builder_end = interval_index.index("def proof_kernel_replay_interval_expr_index_find(", builder_start)
builder = interval_index[builder_start:builder_end]
assert "index.setup_work_ceiling <- build_deadline" in builder
assert builder.index("index.setup_work_ceiling <- build_deadline") < builder.index("for row in 0..<bounds.count", builder.index("build_deadline"))
assert "return true if continuation_reserve >= remaining_at_entry" in builder
assert "available_for_setup: usize = remaining_at_entry - continuation_reserve" in builder
assert "setup_allowance <- available_for_setup if setup_allowance > available_for_setup" in builder
assert "build_deadline: usize = work + setup_allowance" in builder
assert "index.setup_work_ceiling <- 0" in builder
assert "def proof_kernel_replay_interval_expr_index_abandon" in interval_index
abandon_start = interval_index.index("def proof_kernel_replay_interval_expr_index_abandon(")
abandon_end = interval_index.index("def proof_kernel_replay_interval_expr_hash_child(", abandon_start)
assert "index.enabled <- false" in interval_index[abandon_start:abandon_end]
assert "index.setup_work_ceiling <- 0" in interval_index[abandon_start:abandon_end]
assert "index.setup_work_ceiling <- PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in builder
assert "amount > ceiling - work" in interval_index
assert "index.setup_refused <- true" in interval_index
assert "skip_expression_scan <- index.lookup_complete" in bound_lookup
assert "if not skip_expression_scan:" in bound_lookup
assert "proof_kernel_replay_goal_search_expr_equal(nodes, children, bound.term_root, root, work_used)" in bound_lookup
assert "proof_kernel_replay_interval_bound_for_term_with_work(nodes, children, bounds, root, index, work_used)" in interval_lookup
indexed_find_start = interval_index.index("def proof_kernel_replay_interval_expr_index_find(")
indexed_find_end = interval_index.find("\n        def ", indexed_find_start + 4)
indexed_find = interval_index[indexed_find_start:indexed_find_end]
ordered_precheck = function_body(interval_index, "proof_kernel_replay_interval_expr_ordered_precheck")
assert "index.states.resize(nodes.count)" in builder
assert "index.hashes.resize(nodes.count)" in builder
assert "index.matched_rows.resize(nodes.count)" in builder
assert "index.heads.resize(capacity)" in builder
assert "index.tails.resize(capacity)" in builder
assert "index.next_rows.resize(bounds.count)" in builder
assert "slots: usize = nodes.count * 3 + capacity * 2 + bounds.count" in builder
assert "index.next_rows[tail] <- row" in builder
assert "index.tails[slot] <- row" in builder
assert "row: usize = index.heads[" in indexed_find
assert "row <- index.next_rows[row]" in indexed_find
assert "index.hashes[bound.term_root] == query.hash" in indexed_find
assert "proof_kernel_replay_goal_search_expr_equal(nodes, children, bound.term_root, root, work)" in indexed_find
assert "index.lookup_complete <- index.complete" in indexed_find
assert "cached_row: usize = index.matched_rows[root]" in indexed_find
assert "index.matched_rows[root] <- prechecked.row" in indexed_find
assert "cached_row == bounds.count + 1 and index.complete" in indexed_find
assert "index.matched_rows[root] <- bounds.count + 1 if index.complete" in indexed_find
assert "if index.states.count == nodes.count and index.states[root] == 2:" in indexed_find
assert "prechecked: (found: bool, row: usize, scanned_rows: usize) = proof_kernel_replay_interval_expr_ordered_precheck" in indexed_find
assert indexed_find.index("proof_kernel_replay_interval_expr_ordered_precheck") < indexed_find.index("proof_kernel_replay_interval_expr_hash_node(nodes, children, root")
assert "break if rows >= PROOF_KERNEL_REPLAY_INTERVAL_EXPR_PRECHECK_ROWS" in ordered_precheck
assert "not proof_kernel_replay_goal_search_charge(work)" in ordered_precheck
assert "proof_kernel_replay_goal_search_expr_equal(nodes, children, bound.term_root, root, work)" in ordered_precheck
assert ordered_precheck.index("index.hashes[bound.term_root] != index.hashes[root]") < ordered_precheck.index("proof_kernel_replay_goal_search_expr_equal(nodes, children, bound.term_root, root, work)")
assert "index.states[bound.term_root] != 2" in ordered_precheck

print("kernel comparison transport and interval indexing: scans share the goal-search budget")
