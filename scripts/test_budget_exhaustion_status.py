#!/usr/bin/env python3
"""Budget refusals must be retained on the exact proof attempt that refused."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


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


block = body(ROOT / "src/proof/check/block_checker_and_patterns.elisa", "proof_check_block_with_work")
for message in (
    "assert-by runtime guard exceeded the purity analysis work budget",
    "assert-by analysis exceeded its purity source-work budget",
):
    position = 0
    occurrences = 0
    while True:
        position = block.find(message, position)
        if position < 0:
            break
        attempt = block.rfind("proof_add_goal_attempt(", 0, position)
        exhausted = block.find("proof_mark_latest_attempt_exhausted(report,", attempt)
        finding = block.find("proof_add_goal_failure(", attempt)
        assert attempt >= 0 and exhausted >= 0 and finding >= 0 and exhausted < finding < position
        occurrences += 1
        position += len(message)
    assert occurrences > 0, message

core = body(ROOT / "src/proof/check/bounds_and_facts.elisa", "proof_certify_goal_with_rule_core")
quantifier_refusal = core.split("if tactic_work > PROOF_LINEAR_TACTIC_PREFLIGHT_WORK_LIMIT:", 1)[1].split("rule <-", 1)[0]
assert "proof_add_goal_attempt(" in quantifier_refusal
assert "proof_mark_latest_attempt_exhausted(report, true)" in quantifier_refusal
assert "return false" in quantifier_refusal

recording = body(ROOT / "src/proof/model/report_recording.elisa", "proof_mark_latest_attempt_exhausted")
assert "return if not exhausted or report.results.goal_attempts.count == 0" in recording
assert "report.results.goal_attempts[report.results.goal_attempts.count - 1].budget_exhausted <- true" in recording

print("budget refusal: source and tactic exhaustion is attached to the refused goal attempt")
