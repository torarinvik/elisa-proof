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

# The rule itself stays fail-closed until its arena carries authenticated receiver typing.
# This budget guard covers the separate, active comparison-transport rule in the same file.
assert "proof_kernel_replay_primitive_comparison(" not in body_text
assert body_text.count("proof_kernel_replay_witness_marker_cache_fill_with_work(") == 1
assert body_text.count("proof_kernel_replay_primitive_comparison_with_markers_with_work(") == 2
assert body_text.count("work_used > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT") >= 2
assert "work_used, PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT" in body_text
assert "proof_kernel_replay_goal_search_charge(work_used)" in body_text

print("kernel comparison transport: marker and expression scans share the goal-search budget")
