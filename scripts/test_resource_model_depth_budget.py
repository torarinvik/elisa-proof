"""Keep recursive goal replay calls within the function's depth and fuel contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/kernel_replay/resource_model_depth.elisa").read_text(encoding="utf-8")
function_name = "proof_kernel_replay_goal_depth_remaining_with_work"
function_start = source.index(f"def {function_name}(")
function = source[function_start:]
assert "requires remaining > 0" in function
assert "decreases remaining" in function

lines = function.splitlines()
function_indent = len(lines[0]) - len(lines[0].lstrip())
scopes = [(function_indent, False, "function")]
unguarded = []
recursive_calls = []

for line_number, line in enumerate(lines[1:], start=2):
    if line.startswith("        def "):
        break
    stripped = line.strip()
    if not stripped:
        continue
    indent = len(line) - len(line.lstrip())
    while len(scopes) > 1 and scopes[-1][0] >= indent:
        scopes.pop()

    if function_name + "(" in line:
        assert "depth + 1" in line, (line_number, line)
        assert "remaining: remaining - 1" in line, (line_number, line)
        assert "work_used" in line, (line_number, line)
        recursive_calls.append(line)
        guarded = (
            "remaining > 1" in line
            or "remaining > 2" in line
            or scopes[-1][1]
            or any("remaining > 1" in header or "remaining > 2" in header for _, _, header in scopes)
        )
        if not guarded:
            unguarded.append(line)

    # A direct fail-closed return dominates later statements in this lexical scope.
    if stripped.startswith("return false if remaining <= 1"):
        scopes[-1] = (scopes[-1][0], True, scopes[-1][2])

    if stripped.startswith("if ") and stripped.endswith(":"):
        inherited_guard = scopes[-1][1]
        fuel_guard = "remaining > 1" in stripped or "remaining > 2" in stripped
        scopes.append((indent, inherited_guard or fuel_guard, stripped))

assert recursive_calls, "goal replay must retain recursive search paths"

# These two call shapes rely on a data-flow guard rather than a same-line or enclosing
# `remaining > 1` branch. Keep their producer and consumer paired so later refactors
# cannot accidentally call the recursive function with zero remaining fuel.
assert len(unguarded) == 2, unguarded
rewritten_calls = [line for line in unguarded if "rewritten," in line]
widened_calls = [line for line in unguarded if "widened," in line]
assert len(rewritten_calls) == 1, rewritten_calls
assert len(widened_calls) == 1, widened_calls

assert "if remaining > 1 and predicate_root < nodes.count:" in function
assert "witnessed_predicate: mutable bool = false" in function
assert function.count("witnessed_predicate <-") == 1
assert "if witnessed_predicate:" in function
assert "remaining: remaining - 1" in rewritten_calls[0]
assert function.index("if remaining > 1 and predicate_root < nodes.count:") < function.index("if witnessed_predicate:") < function.index(rewritten_calls[0])

widened_refusal = "return false if work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT or widened >= nodes.count or (widened != goal_root and remaining <= 1)"
assert widened_refusal in function
assert "if widened != goal_root:" in function
assert function.index(widened_refusal) < function.index("if widened != goal_root:") < function.index(widened_calls[0])

print(f"resource model depth budget: {len(recursive_calls)} recursive calls decrease positive fuel")
