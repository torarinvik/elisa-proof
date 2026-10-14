"""Guard indexed operator lookup ordering, work caps, and fail-closed chains."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    signature = re.compile(rf"^\s*def {re.escape(name)}\s*\(")
    for start, line in enumerate(lines):
        if signature.match(line):
            indent = len(line) - len(line.lstrip())
            end = start + 1
            while end < len(lines):
                current = lines[end]
                if current.strip() and len(current) - len(current.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[start:end])
    raise AssertionError(f"missing function {name} in {path}")


builder = function_body(ROOT / "src/proof/check/operator_impl_index_build.elisa",
                       "proof_build_operator_impl_index")
query = function_body(ROOT / "src/proof/check/operator_impl_queries.elisa",
                      "proof_report_builtin_operator_impl_exists_with_work")
kernel_query = function_body(ROOT / "src/proof/check/operator_impl_queries.elisa",
                             "proof_report_kernel_operator_impl_exists_with_work")
core = function_body(ROOT / "src/proof/check/api.elisa", "proof_check_core")

# The primitive operator mask and later witness producers must never run against a
# partially built parser-annotation index.
index_call = core.index("proof_build_operator_impl_index(report, &name_index_work)")
mask_call = core.index("proof_source_operator_masks_from_index(report, &name_index_work)")
assert index_call < mask_call
assert "if not operator_index_status.complete:" in core[index_call:mask_call]
assert "return" in core[index_call:mask_call]
assert index_call < core.index("proof_collect_functions_with_region_index")

# Pairing scans and hash-chain allocation/search share explicit work accounting;
# overlong collision chains refuse the source instead of falling back to a scan.
assert "proof_report_source_work_charge(1, source_work)" in builder
assert "PROOF_OPERATOR_IMPL_MAX_BUCKET: usize = 64" in (ROOT / "src/proof/check/operator_impl_index_build.elisa").read_text(encoding="utf-8")
assert "bucket_sizes[slot] > PROOF_OPERATOR_IMPL_MAX_BUCKET" in builder
assert "proof_report_source_work_charge(sview_len(implementation.concrete), source_work)" in builder
assert "proof_report_source_work_charge(sview_len(implementation.protocol), source_work)" in builder
for invariant in (
    "count != report.analysis_1.operator_impls.hashes.count",
    "count != report.analysis_1.operator_impls.next_indices.count",
    "return (false, false) if entry > count",
    "next_entry != count and next_entry >= entry",
    "return (false, false) if entry < count or visits > count",
    "proof_type_audit_work_charge(1, source_work)",
):
    assert invariant in query, invariant

# The kernel's Less-as-Ord correspondence must stay aligned with checker admission.
assert 'protocol != "Ord"' in kernel_query
assert 'proof_report_builtin_operator_impl_exists_with_work(report, concrete, "Less", source_work)' in kernel_query

print("operator impl index: build ordering, bounded lookup, and malformed-chain refusal guarded")
