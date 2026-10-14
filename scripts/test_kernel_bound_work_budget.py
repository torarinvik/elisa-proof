#!/usr/bin/env python3
"""Keep bounded kernel bound-table lookups linear in the shared replay work meter."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/proof/kernel_replay/term_arithmetic.elisa"


def body(name: str) -> str:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            end = index + 1
            while end < len(lines):
                candidate = lines[end]
                if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[index:end])
    raise AssertionError(f"missing kernel helper {name}")


charge = body("proof_kernel_replay_bound_scan_charge_with_work")
for required in (
    "if work_limit > PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT or work_used > work_limit:",
    "work_used <- PROOF_KERNEL_REPLAY_GOAL_SEARCH_WORK_LIMIT + 1",
    "amount > work_limit - work_used",
    "work_used <- work_limit + 1",
):
    assert required in charge, required

lookup = body("proof_kernel_replay_bound_for_with_work")
assert "proof_kernel_replay_bound_scan_charge_with_work(work_used, work_limit, sview_len(name))" in lookup
assert "proof_kernel_replay_bound_scan_charge_with_work(work_used, work_limit, 1 + sview_len(bound_name))" in lookup
assert "if not bounds[index].term_key and bound_name == name" in lookup
assert 'name: name, term_name: "", term_offset: 0, term_key: false' in lookup
assert "has_lower: false, lower: 0, has_upper: false, upper: 0" in lookup

for operation in ("add_lower", "add_upper"):
    helper = body(f"proof_kernel_replay_{operation}_with_work")
    assert "proof_kernel_replay_bound_scan_charge_with_work(work_used, work_limit, sview_len(name))" in helper
    assert "proof_kernel_replay_bound_scan_charge_with_work(work_used, work_limit, 1 + sview_len(bound.name))" in helper
    assert "if not bound.term_key and bound.name == name" in helper
    assert "proof_kernel_replay_bound_scan_charge_with_work(work_used, work_limit, 1)" in helper
    assert "return false if not proof_kernel_replay_bound_scan_charge_with_work" in helper
    if operation == "add_lower":
        assert "bound.lower <- value if not old_has or value > old_value" in helper
        assert "has_lower: true, lower: value" in helper
        assert "has_upper: false, upper: 0" in helper
    else:
        assert "bound.upper <- value if not old_has or value < old_value" in helper
        assert "has_lower: false, lower: 0" in helper
        assert "has_upper: true, upper: value" in helper

print("kernel bound scans: lookup and insertion debit names and rows; exhaustion fails closed")
