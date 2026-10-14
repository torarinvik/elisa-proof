"""Keep direct frame-write classification on its shared source-work meter."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/check/function_contracts_and_frames.elisa").read_text(encoding="utf-8")
work_source = (ROOT / "src/proof/check/frame_write_work.elisa").read_text(encoding="utf-8")


def function_body(text: str, name: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\s*def {re.escape(name)}\b", line))
    indent = len(lines[start]) - len(lines[start].lstrip())
    result = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        result.append(line)
    return "\n".join(result)


place_text = function_body(work_source, "proof_frame_write_place_text_work")
for component in ("place.root", "place.field", "place.field2", "place.field3"):
    assert f"sview_len({component})" in place_text
assert "amount * 4" in place_text
assert "proof_frame_source_work_take" in place_text

refusal = function_body(work_source, "proof_frame_write_scan_refusal")
assert "report.proof_frame_obligation(false)" in refusal
assert '"frame-write-opaque"' in refusal

write = function_body(source, "proof_check_direct_frame_write")
assert write.index("changes.count == 0 and preserves.count == 0") < write.index("proof_frame_place(target)")
assert "proof_frame_write_places_text_reserve(changes, preserves" in write
assert "changes.count > PROOF_LINEAR_SAFETY_WORK_LIMIT - preserves.count" in write
assert "proof_frame_write_expression_cost(target, report, name, line)" in write
assert "proof_frame_write_expression_passes_reserve(expression_cost.cost, 3" in write
assert "proof_frame_write_expression_passes_reserve(expression_cost.cost, 4" in write
assert "proof_frame_write_alias_scan_reserve(expression_cost.cost, place_count" in write
assert write.index("proof_frame_write_expression_passes_reserve(expression_cost.cost, 3") < write.index("proof_frame_place(target)")
assert "parameter_probe_cost: usize = 1 + sview_len(decoded.place.root)" in write
assert "names.count * parameter_probe_cost" in write
assert "proof_frame_write_scan_refusal(report, name, line)" in write
cost_helper = function_body(work_source, "proof_frame_write_expression_cost")
assert "proof_linear_safety_expr_cost_with_work(target, &budget, &exhausted)" in cost_helper
reserve_helper = function_body(work_source, "proof_frame_write_expression_passes_reserve")
assert "proof_linear_safety_work_charge_scaled(&budget, &exhausted, cost, passes)" in reserve_helper
alias_reserve = function_body(work_source, "proof_frame_write_alias_scan_reserve")
assert "proof_linear_safety_work_charge_product4_with_work(&budget, &exhausted, place_count, cost, cost, 1, 8)" in alias_reserve

print("frame-write classification: target and path scans share bounded frame work")
