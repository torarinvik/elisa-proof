#!/usr/bin/env python3
"""Prevent validation memo reuse across caller-mutable kernel arenas."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
validation_path = ROOT / "src/proof/kernel_replay/tactic_arena_validation.elisa"
api_path = ROOT / "src/proof/kernel_replay/api.elisa"
tactic_path = ROOT / "src/proof/kernel_replay/tactic_replay.elisa"


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
