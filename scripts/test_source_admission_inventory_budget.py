"""Keep source admission and structural-termination scans inside shared work budgets."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/replay/api.elisa").read_text(encoding="utf-8")
lines = source.splitlines()
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

print("source admission inventory budget: fallback scans refuse on shared-work exhaustion")
