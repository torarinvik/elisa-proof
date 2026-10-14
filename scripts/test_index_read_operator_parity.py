"""Keep overloaded indexed reads opaque until replay carries builtin type evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith(f"def {name}("):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following.strip())
            return "\n".join(body)
    raise AssertionError(f"function {name} not found in {path}")


dispatch = (ROOT / "src/proof/linear/congruence_goals.elisa").read_text(encoding="utf-8")
assert "proof_index_read_equality_goal(facts, goal" not in dispatch
assert "resolved receiver-type witness" in dispatch
replay_dispatch = (ROOT / "src/proof/kernel_replay/resource_model.elisa").read_text(encoding="utf-8")
assert "proof_kernel_replay_index_read_equality(nodes, children, facts, goal_root" not in replay_dispatch
assert "resolved receiver-type witness" in replay_dispatch
producer_rule = function_body(ROOT / "src/proof/linear/index_read_equalities.elisa", "proof_index_read_equality_goal")
kernel_rule = function_body(ROOT / "src/proof/kernel_replay/index_read_equalities.elisa", "proof_kernel_replay_index_read_equality")
assert producer_rule.splitlines()[-1] == "return false"
assert kernel_rule.splitlines()[-1] == "return false"
assert "proof_expr_equal" not in producer_rule
assert "proof_kernel_replay_expr_equal" not in kernel_rule
assert not any(line.startswith("for ") for line in producer_rule.splitlines() + kernel_rule.splitlines())

positive = (ROOT / "examples/index_read_equality.elisa").read_text(encoding="utf-8")
negative = (ROOT / "examples/rejected_index_read_equality.elisa").read_text(encoding="utf-8")
assert "def indexed_disequality_at_equal_index" in positive
assert "requires rows[cursor] != 64\n    ensure rows[3] != 64" in positive
assert "def indexed_disequality_from_negated_equality" in positive
assert "requires not (rows[cursor] == 64)\n    ensure rows[3] != 64" in positive
assert "def rejected_disequality_different_index" in negative
assert "requires rows[cursor] != 64\n    ensure rows[3] != 64" in negative
runtime = (ROOT / "scripts/test_index_read_equality.py").read_text(encoding="utf-8")
assert '"index_read_equality.elisa", "failed"' in runtime
assert '"open_indexed_prefix_reasoning.elisa", "failed"' in runtime
assert '"open_index_window_disjunctions.elisa", "failed"' in runtime
assert '"rejected_index_read_equality.elisa", "failed"' in runtime
assert '"rejected_disequality_different_index"' in runtime

print("indexed-read transport stays disabled in both producer and replay without builtin-type evidence")
