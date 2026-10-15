"""Kernel hostile indexes are range-checked before they are dereferenced."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def body(path: str, function: str) -> str:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\s*def {re.escape(function)}\b", line))
    indent = len(lines[start]) - len(lines[start].lstrip())
    result = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        result.append(line)
    return "\n".join(result)


sort_lookup = body("src/proof/kernel_replay/bound_closure.elisa", "proof_kernel_replay_name_equality_sort_with_work")
assert sort_lookup.index("root >= nodes.count") < sort_lookup.index("nodes[root].kind")

linear_or = body("src/proof/kernel_replay/linear_arithmetic.elisa", "proof_kernel_replay_linear_is_or")
assert linear_or.index("root >= nodes.count") < linear_or.index("proof_kernel_replay_valid(nodes, root)") < linear_or.index("nodes[root].kind")

# Shared metering adapters are themselves hostile-index boundaries: range validation must
# complete before any attempt to measure serialized text through the indexed node.
for path, function, first_field in (
    ("src/proof/kernel_replay/goal_metered_constants.elisa", "proof_kernel_replay_goal_search_charge_node_text", "kind"),
    ("src/proof/kernel_replay/scalar_witness_work.elisa", "proof_kernel_replay_scalar_witness_charge_node_text", "kind"),
    ("src/proof/kernel_replay/term_arithmetic.elisa", "proof_kernel_replay_constant_int_charge_node_text", "kind"),
):
    meter = body(path, function)
    assert "return false if root >= nodes.count" in meter
    assert meter.index("return false if root >= nodes.count") < meter.index(f"nodes[root].{first_field}")
    assert "root >= nodes.count or" not in meter

arena_validation = (ROOT / "src/proof/kernel_replay/tactic_arena_validation.elisa").read_text(encoding="utf-8")
assert "root: usize = goal_root if root_index == 0 else facts[root_index - 1]" not in arena_validation
assert arena_validation.count("root <- facts[root_index - 1]") == 2

direct_reference = body("src/proof/kernel_replay/resource_state.elisa", "proof_kernel_replay_resource_value_term_is_direct_reference")
assert direct_reference.index("root >= nodes.count") < direct_reference.index("nodes[root].kind")

resource_parameters = body("src/proof/kernel_replay/resource_state.elisa", "proof_kernel_replay_resource_parameters")
assert resource_parameters.index("root >= nodes.count") < resource_parameters.index("nodes[root].kind")

for path, function in (
    ("src/proof/kernel_replay/goal_metered_unsigned_widening.elisa", "proof_kernel_replay_signed_expression_safe_with_bounds_goal_cached_work"),
    ("src/proof/kernel_replay/unsigned_bounds.elisa", "proof_kernel_replay_unsigned_expression_safe_with_replay_work"),
):
    walker = body(path, function)
    assert "if not child.known\n" in walker
    assert "if child.value >= nodes.count\n" in walker
    assert walker.index("if child.value >= nodes.count\n") < walker.index("nodes[child.value].kind != \"resource-call-arg\"")

# No kernel guard may combine an index's upper-bound test with a read through the same index.
dangerous = re.compile(r"(?P<index>[A-Za-z_]\w*)\s*>=\s*nodes\.count[^\n]*nodes\[(?P=index)\]")
guarded_and = re.compile(r"(?P<index>[A-Za-z_]\w*)\s*<\s*nodes\.count\s+and\s+nodes\[(?P=index)\]")
for path in (ROOT / "src/proof/kernel_replay").rglob("*.elisa"):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        assert not dangerous.search(line), f"{path.relative_to(ROOT)}:{number}: {line.strip()}"
        if not line.lstrip().startswith("ensure "):
            assert not guarded_and.search(line), f"{path.relative_to(ROOT)}:{number}: {line.strip()}"

close_terms = body("src/proof/kernel_replay/goal_metered_interval.elisa", "proof_kernel_replay_close_term_equalities_with_goal_work")
assert "while steps < 8" in close_terms
assert close_terms.index("break if root >= nodes.count") < close_terms.index('nodes[root].kind != "paren"')

refutation = body("src/proof/kernel_replay/arithmetic_refutation.elisa", "proof_kernel_replay_facts_arithmetically_inconsistent_with_work")
assert "if root < nodes.count:\n                    if nodes[root].kind != \"binary\":" in refutation

print("kernel index-read guard: hostile node indexes are checked before dereference")
