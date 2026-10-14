#!/usr/bin/env python3
"""Keep public typed tactic transitions on one cumulative type-checking budget."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
api = ROOT / "src/proof/kernel_replay/api.elisa"
formation = ROOT / "src/proof/kernel_replay/proposition_formation.elisa"
tactic_json = ROOT / "src/proof/tactic_json.elisa"
tactic_replay = ROOT / "src/proof/kernel_replay/tactic_replay.elisa"
branch_report = ROOT / "src/proof/kernel_replay/tactic_branch_report.elisa"


def body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            end = index + 1
            while end < len(lines):
                following = lines[end]
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[index:end])
    raise AssertionError(f"missing {name} in {path}")


step = body(api, "proof_kernel_replay_tactic_step_typed")
assert "proof_kernel_replay_build_typing_index(environment, &typing_work_used)" in step
assert "before_facts, before_goal, &typing_work_used" in step
assert "after_facts, after_goal, &typing_work_used" in step
assert "typing_index_work" not in step
assert "before_typing_work" not in step
assert "after_typing_work" not in step
assert "typing_work_used > ElisaProofKernelCore::PROOF_KERNEL_TYPE_WORK_BUDGET" in step
assert "sview_len(action) > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT / 64" in step
assert "sview_len(detail) > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT / 4" in step
assert "action == \"rewrite\"" in step
assert step.count("proof_kernel_replay_term_sort(nodes, children, environment, typing_index.index, argument") == 1
assert "argument_sort_cache <- proof_kernel_replay_term_sort(nodes, children, environment, typing_index.index, argument" in step
assert "proof_kernel_replay_sort_equal(argument_sort_cache, secondary_sort" in step
assert 'argument_sort_cache.family != "integer" and argument_sort_cache.family != "character" and argument_sort_cache.family != "boolean" and argument_sort_cache.family != "string"' in step

branch_step = body(branch_report, "proof_kernel_replay_tactic_branch_report_with_work")
assert "proof_kernel_replay_goal_search_charge_product(step_work, sview_len(action), 4)" in branch_step
transition_step = body(tactic_replay, "proof_kernel_replay_tactic_step_body")
assert "proof_kernel_replay_goal_search_charge_product(step_work, sview_len(action), 64)" in transition_step
assert "proof_kernel_replay_goal_search_charge_product(step_work, sview_len(detail), 4)" in transition_step

branch = body(api, "proof_kernel_replay_tactic_branch_typed")
assert "proof_kernel_replay_build_typing_index(environment, &typing_work_used)" in branch
for state in ("parent_facts, parent_goal", "left_facts, left_goal", "right_facts, right_goal"):
    assert f"{state}, &typing_work_used" in branch
assert "typing_work_used > ElisaProofKernelCore::PROOF_KERNEL_TYPE_WORK_BUDGET" in branch
assert "proof_kernel_replay_tactic_branch_report_with_work" in branch
assert "proof_kernel_replay_tactic_branch_report(nodes" not in branch

state = body(formation, "proof_kernel_replay_typed_proposition_state_valid_with_index")
assert "work_used > ElisaProofKernelCore::PROOF_KERNEL_TYPE_WORK_BUDGET" in state
assert "proof_kernel_replay_typed_proposition_at(nodes, children, environment, typing_index" in state
source_run = body(tactic_json, "proof_tactic_json_run_source_candidate")
assert "proof_float_mode <- attempt.float_mode" in source_run
assert "proof_float_mode <- previous_float_mode" in source_run
print("typed tactic replay: proposition states share the public call's cumulative type-work budget")
