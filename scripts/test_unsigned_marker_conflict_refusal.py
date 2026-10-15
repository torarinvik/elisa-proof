"""Source guards for refusing ambiguous same-spelling scalar type markers."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    signature = re.compile(rf"^\s*def {re.escape(name)}\s*\(")
    for start, line in enumerate(lines):
        if signature.match(line):
            indent = len(line) - len(line.lstrip())
            end = start + 1
            while end < len(lines):
                current = lines[end]
                if current.strip() and len(current) - len(current.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[start:end])
    raise AssertionError(f"missing function {name} in {path}")


def assert_conflicts_fail_closed(path: Path, name: str, mismatch: str) -> None:
    body = function_body(path, name)
    assert mismatch in body
    assert "work_used <- PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT + 1" in body
    assert "return 0" in body


def assert_uses_shared_unsigned_conflict_check(path: Path, name: str) -> None:
    body = function_body(path, name)
    assert "proof_kernel_replay_unsigned_width_from_markers_with_goal_work" in body


def main() -> None:
    replay = ROOT / "src/proof/kernel_replay"
    assert_conflicts_fail_closed(
        replay / "goal_metered_conditional_plans.elisa",
        "proof_kernel_replay_unsigned_width_from_markers_with_goal_work",
        "marker.width != width",
    )
    assert_uses_shared_unsigned_conflict_check(
        replay / "goal_metered_interval.elisa",
        "proof_kernel_replay_unsigned_marker_width_for_name_with_goal_work",
    )
    assert_conflicts_fail_closed(
        replay / "goal_metered_interval.elisa",
        "proof_kernel_replay_signed_marker_width_for_term_with_goal_work",
        "marker.width != width",
    )
    assert "place.width != width" in function_body(
        replay / "goal_metered_interval.elisa",
        "proof_kernel_replay_signed_marker_width_for_term_with_goal_work",
    )
    assert_conflicts_fail_closed(
        replay / "goal_metered_linear_disequality.elisa",
        "proof_kernel_replay_linear_place_marker_width_with_work",
        "value.value != width",
    )
    assert_uses_shared_unsigned_conflict_check(
        replay / "goal_metered_linear_disequality.elisa",
        "proof_kernel_replay_linear_unsigned_marker_width_from_markers_with_work",
    )
    assert_conflicts_fail_closed(
        replay / "goal_metered_linear_disequality.elisa",
        "proof_kernel_replay_linear_element_width_with_work",
        "marker.width != width",
    )

    source = function_body(
        ROOT / "src/proof/check/symbol_and_move_state.elisa",
        "proof_resymbolize_binding",
    )
    assert "elif current_width != marker.width" in source
    assert "cascaded_widths[target_index] <- -1" in source
    assert "cascaded_widths[target_index] <= 0" in source
    assert "marker.width < current_width" not in source
    print("ambiguous scalar widths fail closed in replay and source resymbolization")


if __name__ == "__main__":
    main()
