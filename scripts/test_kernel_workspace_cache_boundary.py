#!/usr/bin/env python3
"""Prevent validation memo reuse across caller-mutable kernel arenas."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
validation_path = ROOT / "src/proof/kernel_replay/tactic_arena_validation.elisa"
api_path = ROOT / "src/proof/kernel_replay/api.elisa"
tactic_path = ROOT / "src/proof/kernel_replay/tactic_replay.elisa"
workspace_path = ROOT / "src/proof/kernel_replay/validation_workspace.elisa"


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


validator = body(validation_path, "proof_kernel_replay_arena_valid_with_workspace")
assert "proof_kernel_replay_arena_valid_with_workspace_limit(nodes, children, facts, goal_root, workspace, PROOF_KERNEL_REPLAY_ARENA_WORK_BUDGET, false)" in validator

trace_validator = body(validation_path, "proof_kernel_replay_arena_valid_with_trace_workspace")
assert "proof_kernel_replay_arena_valid_with_workspace_limit(nodes, children, facts, goal_root, workspace, work_limit, true)" in trace_validator
assert "one unchanged arena reference" in trace_validator
all_kernel = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src/proof/kernel_replay").rglob("*.elisa"))
assert all_kernel.count("workspace, work_limit, true)") == 1

# Report validation accounts for arena traversal cumulatively, separately from logical search.
# The per-call validator's `work_used` is scratch accounting and must be charged before the next
# root query can obtain another allowance from the shared workspace.
workspace_source = workspace_path.read_text(encoding="utf-8")
assert re.search(
    r"\n\s*private:\n\s*# Keep the cumulative arena meter private to this module\.[\s\S]*?\n\s*kernel_goal_arena_work_used: mutable usize",
    workspace_source,
), "callers must not reset the cumulative arena-work ceiling"
workspace_fields = workspace_source.split("def proof_kernel_replay_validation_workspace_new", 1)[0]
assert workspace_fields.index("allow_replayed_dependency_memo:") < workspace_fields.index(
    "private:\n                # Keep the cumulative arena meter private"
)
assert workspace_fields.rstrip().endswith("kernel_goal_arena_work_used: mutable usize")
counter_owner_paths = {
    workspace_path,
    api_path,
}
external_counter_mentions = [
    str(path.relative_to(ROOT))
    for path in (ROOT / "src").rglob("*.elisa")
    if path not in counter_owner_paths and "kernel_goal_arena_work_used" in path.read_text(encoding="utf-8")
]
assert not external_counter_mentions, external_counter_mentions
workspace_constructor = body(workspace_path, "proof_kernel_replay_validation_workspace_new")
assert "kernel_goal_arena_work_used: 0" in workspace_constructor

goal_arena_validator = body(api_path, "proof_kernel_replay_arena_valid_with_goal_work_and_workspace")
for required in (
    "workspace.kernel_goal_arena_work_used > PROOF_KERNEL_REPLAY_ARENA_WORK_BUDGET",
    "work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT",
    "PROOF_KERNEL_REPLAY_ARENA_WORK_BUDGET - workspace.kernel_goal_arena_work_used",
    "report_remaining: usize = PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT - work_used",
    "arena_limit: usize = remaining if remaining < report_remaining else report_remaining",
    "if arena_limit == 0:",
    "workspace, arena_limit, false)",
    "arena_work: usize = workspace.work_used",
    "workspace.kernel_goal_arena_work_used <- PROOF_KERNEL_REPLAY_ARENA_WORK_BUDGET",
    "workspace.kernel_goal_arena_work_used <- workspace.kernel_goal_arena_work_used + arena_work",
):
    assert required in goal_arena_validator, required
assert "if not proof_kernel_replay_goal_search_charge_amount(work_used, arena_work):" in goal_arena_validator
assert goal_arena_validator.index("workspace.kernel_goal_arena_work_used > PROOF_KERNEL_REPLAY_ARENA_WORK_BUDGET") < goal_arena_validator.index("PROOF_KERNEL_REPLAY_ARENA_WORK_BUDGET - workspace.kernel_goal_arena_work_used")
assert goal_arena_validator.index("work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT") < goal_arena_validator.index("report_remaining: usize = PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT - work_used")
assert goal_arena_validator.index("arena_limit: usize = remaining if remaining < report_remaining else report_remaining") < goal_arena_validator.index("workspace, arena_limit, false)")
assert goal_arena_validator.index("valid: bool =") < goal_arena_validator.index("arena_work: usize = workspace.work_used")
assert goal_arena_validator.index("workspace.kernel_goal_arena_work_used <- workspace.kernel_goal_arena_work_used + arena_work") < goal_arena_validator.index("if not valid and arena_work >= arena_limit")
assert goal_arena_validator.index("workspace.kernel_goal_arena_work_used <- workspace.kernel_goal_arena_work_used + arena_work") < goal_arena_validator.index("if not proof_kernel_replay_goal_search_charge_amount(work_used, arena_work):")

per_call_validator = body(validation_path, "proof_kernel_replay_arena_valid_with_workspace_limit")
assert per_call_validator.index("workspace.work_used <- 0") < per_call_validator.index("initialize_cache:")

# Every API endpoint accepting a validation workspace either validates in its own body
# or delegates to an endpoint that does. Discover these signatures instead of keeping a
# partial hand-maintained list: adding a new workspace API must extend this audit.
api = api_path.read_text(encoding="utf-8")
workspace_api_names = re.findall(
    r"^\s*def\s+(\w+)\b[^\n]*ProofKernelReplayValidationWorkspace&",
    api,
    re.MULTILINE,
)
assert workspace_api_names
for name in workspace_api_names:
    endpoint = body(api_path, name)
    validates_here = any(
        helper in endpoint
        for helper in (
            "proof_kernel_replay_arena_valid_with_workspace(",
            "proof_kernel_replay_arena_valid_with_goal_work_and_workspace(",
        )
    )
    delegates_to_validated_endpoint = (
        name == "proof_kernel_replay_proposition_formation_report_with_cached_globals"
        and "proof_kernel_replay_proposition_formation_report_with_cached_globals_and_work(" in endpoint
    )
    assert validates_here or delegates_to_validated_endpoint, name
    if name == "proof_kernel_replay_arena_valid_with_goal_work_and_workspace":
        assert "workspace, arena_limit, false)" in endpoint
    else:
        assert "arena_valid_with_workspace_limit" not in endpoint, name

# The private reuse path validates every root against the exact same arrays before tactic replay
# can mutate the arena. Once state comparison begins, the first mutation is an append-only rewrite.
tactic_api_wrapper = body(api_path, "proof_kernel_replay_tactic_step_with_trace_work")
assert (
    "proof_kernel_replay_tactic_step_impl_with_trace_work(nodes, children, action, accepted, "
    "before_solved, after_solved, before_facts, before_goal, after_facts, after_goal, "
    "argument, has_argument, secondary, has_secondary, argument_index, has_argument_index, "
    "detail, false, trace_work)"
) in tactic_api_wrapper
tactic_body = body(tactic_path, "proof_kernel_replay_tactic_step_body")
for validation in (
    "proof_kernel_replay_arena_valid_with_trace_workspace(nodes, children, before_facts, before_goal",
    "proof_kernel_replay_arena_valid_with_trace_workspace(nodes, children, after_facts, after_goal",
    "proof_kernel_replay_arena_valid_with_trace_workspace(nodes, children, [], argument",
    "proof_kernel_replay_arena_valid_with_trace_workspace(nodes, children, [], secondary",
):
    assert validation in tactic_body
first_tactic_append = tactic_body.find("nodes.push")
assert first_tactic_append < 0 or first_tactic_append > tactic_body.index("if not arena_prevalidated:")

print("kernel validation cache: public workspaces revalidate; memo reuse is private to unchanged tactic arenas")
