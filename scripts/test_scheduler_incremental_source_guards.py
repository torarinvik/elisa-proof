"""Prevent declaration schedulers from rescanning all earlier findings per node."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
proof = ROOT / "src/proof/check"


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return line + "\n" + "\n".join(body)
    raise AssertionError(f"function {name} not found in {path}")


indexes = proof / "verification_findings.elisa"
for name, index_type in (
    ("proof_function_finding_summary_extend", "ProofFunctionFindingSummary"),
    ("proof_lemma_finding_summary_extend", "ProofLemmaFindingSummary"),
):
    body = function_body(indexes, name)
    assert f"summary: mutable {index_type}&" in body
    assert "summary.findings_seen > report.results.findings.count" in body
    assert "summary.findings_seen..<report.results.findings.count" in body
    assert "summary.findings_seen <- report.results.findings.count" in body
    assert "proof_report_source_work_charge(1, work)" in body
    assert "for finding in report.results.findings" not in body

function_finding_build = function_body(indexes, "proof_function_finding_duplicate_index_build")
assert "duplicate_slots_by_row.push(slot)" in function_finding_build
assert "duplicate_slot_clean.push(true)" in function_finding_build
assert "proof_report_source_work_charge(6, work)" in function_finding_build
function_finding_extend = function_body(indexes, "proof_function_finding_summary_extend")
assert "if finding.owner_line != 0:" in function_finding_extend
assert "proof_finding_source_identity_slot(finding.name, finding.owner_line, finding.owner_offset" in function_finding_extend
ownerless_duplicate_path = function_finding_extend.split('if finding.owner == "":', 1)[1].split("row: mutable usize", 1)[0]
assert "proof_function_finding_mark_ambiguous_slot(finding, summary, duplicate.slot, work)" in ownerless_duplicate_path
assert "continue" in ownerless_duplicate_path
assert "while row < count" not in ownerless_duplicate_path
assert "proof_function_finding_mark_row(finding, functions, summary, row, work)" in function_finding_extend
for accessor in (
    "proof_function_finding_row_clean",
    "proof_function_finding_row_widened",
    "proof_function_finding_row_contract_type",
    "proof_function_finding_row_unverified",
    "proof_function_finding_row_lemma_unverified",
):
    assert "duplicate_slots_by_row[row]" in function_body(indexes, accessor)

function_schedule = proof / "function_verification_schedule.elisa"
function_body_text = function_body(function_schedule, "proof_compute_verified_functions")
assert "proof_function_finding_summary_build(report, functions, &schedule_work)" in function_body_text
assert function_body_text.count(
    "proof_function_finding_summary_extend(report, functions, &function_findings, &schedule_work)"
) >= 2, "new findings must be indexed after each scheduled component"
schedule_path = proof / "verification_schedule.elisa"
function_node = function_body(schedule_path, "proof_check_scheduled_function")
assert "proof_function_finding_row_contract_type(function_findings, target, schedule_work)" in function_node

lemma_schedule = schedule_path
lemma_body = function_body(lemma_schedule, "proof_compute_verified_lemmas")
assert "proof_lemma_finding_summary_build(report, lemmas, &source_scan_work)" in lemma_body
assert "proof_lemma_finding_summary_extend(report, lemmas, &lemma_findings, &source_scan_work)" in lemma_body
lemma_node = function_body(lemma_schedule, "proof_check_scheduled_lemma")
assert "lemma_findings.contract_type[target]" in lemma_node

print("scheduler source guards: findings are indexed incrementally with fail-closed work charging")
