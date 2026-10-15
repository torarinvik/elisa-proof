"""Keep source admission and structural-termination scans inside shared work budgets."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/replay/api.elisa").read_text(encoding="utf-8")
boundary_source = (ROOT / "src/proof/replay/boundary_trace_shapes.elisa").read_text(encoding="utf-8")
summary_call_source = (ROOT / "src/proof/replay/summary_call_sites.elisa").read_text(encoding="utf-8")
loop_control_source = (ROOT / "src/proof/replay/boundary_loop_fact_sources.elisa").read_text(encoding="utf-8")
loop_entry_source = (ROOT / "src/proof/replay/source_binding_validation/loop_entry_certificates.elisa").read_text(encoding="utf-8")
lines = source.splitlines()


def function_body(text: str, name: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = [line]
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"function {name} not found")


start = next(i for i, line in enumerate(lines) if "def proof_check_and_replay_with_source[" in line)
indent = len(lines[start]) - len(lines[start].lstrip())
body = []
for line in lines[start + 1:]:
    if line.strip() and len(line) - len(line.lstrip()) <= indent:
        break
    body.append(line)
body_text = "\n".join(body)
scan = re.search(
    r"for finding_index in 0\.\.\<report\.results\.findings\.count.*?(?=\n\s{28}if source_binding_finding ==)",
    body_text,
    re.S,
)
assert scan is not None, "source-obligation finding lookup disappeared"
scan_text = scan.group()
comparison = scan_text.index('finding.kind == "source-obligation-inventory"')
for charge in (
    "proof_replay_source_work_charge(1, source_work)",
    "proof_replay_source_work_charge(sview_len(finding.kind), source_work)",
    'proof_replay_source_work_charge(sview_len("source-obligation-inventory"), source_work)',
    "proof_replay_source_work_charge(sview_len(finding.name), source_work)",
    "proof_replay_source_work_charge(sview_len(finding.message), source_work)",
    'proof_replay_source_work_charge(sview_len("a supported source postcondition has no distinct source-bound proof attempt"), source_work)',
):
    assert charge in scan_text[:comparison], charge
assert scan_text.count("return ProofCheckedView{") == 6, "budget exhaustion must refuse the checked view"
assert body_text.count("source_work: mutable usize = 0") == 1, "one shared meter must cover lookup and admission"
unsupported_helper = (ROOT / "src/proof/model/report_focused_source_ensures.elisa").read_text(encoding="utf-8")
assert "def proof_source_literal_ensure_inventory_has_unsupported_with_work(" in unsupported_helper
assert "proof_report_source_work_charge(1, source_work)" in unsupported_helper
assert "proof_report_source_work_charge(sview_len(expected.name), source_work)" in unsupported_helper
assert "proof_source_literal_ensure_inventory_has_unsupported(" not in source
assert "proof_source_literal_ensure_inventory_has_unsupported_with_work(literal_inventory, source_work)" in body_text
assert "if not unsupported_inventory.complete" in body_text

# Loop-control validation has a private per-trace cap, but its consumed work must
# still debit the shared report budget on both success and rejection. Keep the
# result capture separate so a failed validation cannot return before accounting.
boundary = function_body(boundary_source, "proof_replay_boundary_trace_shape_valid_with_cache")
loop_branch = boundary.split('if trace.kind in {"loop-condition", "loop-invariant", "loop-range"}:', 1)[1].split(
    'if trace.kind in {"runtime-assert", "runtime-guard"}:', 1
)[0]
control_result = loop_branch.index(
    "control_valid: bool = (proof_replay_control_loop_fact_source_with_work(report, trace, &control_work)"
)
remaining_guard = loop_branch.index("return false if source_work > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT")
remaining = loop_branch.index("remaining_batch_work: usize = PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT - source_work")
allowance = loop_branch.index("control_allowance: usize = PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT")
zero_allowance = loop_branch.index("return false if control_allowance == 0")
seed = loop_branch.index("control_work_seed: usize = PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT - control_allowance")
meter = loop_branch.index("control_work: mutable usize = control_work_seed")
meter_bounds = loop_branch.index(
    "control_work < control_work_seed or control_work > PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT"
)
consumed = loop_branch.index("control_work_used: usize = control_work - control_work_seed")
shared_debit = loop_branch.index("proof_replay_source_work_charge_or_exhaust(control_work_used, source_work)")
acceptance = loop_branch.index("return control_valid")
assert remaining_guard < remaining < allowance < zero_allowance < seed < meter < control_result < meter_bounds < consumed < shared_debit < acceptance
assert "control_work < control_work_seed" in loop_branch
assert "control_work > PROOF_REPLAY_CONTROL_SOURCE_WORK_LIMIT" in loop_branch
assert "return false if not control_valid" not in loop_branch

# The call-argument comparator normally uses a SUMMARY meter. Loop validation uses
# this bridge so that nested comparison work stays within the remaining CONTROL budget.
limited_argument_equal = function_body(
    summary_call_source, "proof_replay_summary_call_argument_equal_with_limit"
)
for rejected_budget in (
    "if work_limit > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT:\n                complete <- false\n                return false",
    "if work > work_limit:\n                work <- work_limit\n                complete <- false\n                return false",
    "if remaining_work == 0:\n                complete <- false\n                return false",
    "if virtual_work < virtual_seed or virtual_work > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT:\n                work <- work_limit\n                complete <- false\n                return false",
    "if consumed_work > remaining_work:\n                work <- work_limit\n                complete <- false\n                return false",
):
    assert rejected_budget in limited_argument_equal, rejected_budget
for fragment in (
    "remaining_work: usize = work_limit - work",
    "virtual_seed: usize = PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT - remaining_work",
    "virtual_work: mutable usize = virtual_seed",
    "proof_replay_summary_call_argument_equal_with_work",
    "consumed_work: usize = virtual_work - virtual_seed",
    "work <- work + consumed_work",
):
    assert fragment in limited_argument_equal, fragment
assert (
    limited_argument_equal.index("if work_limit > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT:")
    < limited_argument_equal.index("if work > work_limit:")
    < limited_argument_equal.index("remaining_work: usize = work_limit - work")
    < limited_argument_equal.index("if remaining_work == 0:")
    < limited_argument_equal.index("virtual_seed: usize = PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT - remaining_work")
    < limited_argument_equal.index("matches: bool = proof_replay_summary_call_argument_equal_with_work")
    < limited_argument_equal.index("consumed_work: usize = virtual_work - virtual_seed")
    < limited_argument_equal.index("if consumed_work > remaining_work:")
    < limited_argument_equal.index("work <- work + consumed_work")
    < limited_argument_equal.index("matches and complete")
), "nested summary work must be bounded and debited before either result is returned"
assert "proof_replay_summary_call_argument_equal_with_limit" in loop_control_source
assert "proof_replay_summary_call_argument_equal_with_limit" in loop_entry_source

charge_or_exhaust = function_body(source, "proof_replay_source_work_charge_or_exhaust")
assert charge_or_exhaust.index("proof_replay_source_work_charge(amount, source_work)") < charge_or_exhaust.index(
    "source_work <- PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT + 1"
)
assert charge_or_exhaust.index(
    "source_work <- PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT + 1"
) < charge_or_exhaust.index("false")

print("source-work admission guards: fallback scans and failed loop-control checks debit shared budgets")
