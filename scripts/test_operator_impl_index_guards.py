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
scope_collect = function_body(ROOT / "src/proof/check/operator_impl_index_build.elisa",
                              "proof_operator_scope_collect")
scope_body = function_body(ROOT / "src/proof/check/operator_impl_index_build.elisa",
                           "proof_operator_scope_body_mask")
scope_index_build = function_body(ROOT / "src/proof/check/operator_impl_index_build.elisa",
                                 "proof_operator_scope_index_build")
scope_lookup = function_body(ROOT / "src/proof/check/operator_impl_index_build.elisa",
                             "proof_operator_scope_index_mask_at")
query = function_body(ROOT / "src/proof/check/operator_impl_queries.elisa",
                      "proof_report_builtin_operator_impl_exists_with_work")
kernel_query = function_body(ROOT / "src/proof/check/operator_impl_queries.elisa",
                             "proof_report_kernel_operator_impl_exists_with_work")
core = function_body(ROOT / "src/proof/check/api.elisa", "proof_check_core")
annotation_lookup = function_body(ROOT / "src/proof/check/source_operator_guard.elisa",
                                  "proof_source_primitive_operator_overloaded_with_work")
report_reset = function_body(ROOT / "src/proof/check/source_effect_index_reset.elisa",
                             "proof_source_analysis_indexes_reset")

# The primitive operator mask and later witness producers must never run against a
# partially built parser-annotation index.
index_call = core.index("proof_build_operator_impl_index(report, &name_index_work)")
mask_call = core.index("proof_source_operator_masks_from_index(report, &name_index_work)")
assert index_call < mask_call
assert "if not operator_index_status.complete:" in core[index_call:mask_call]
assert "return" in core[index_call:mask_call]
assert index_call < core.index("proof_collect_functions_with_region_index")

# Per-type dunder masks must come from parser-owned declaration bodies joined by exact source
# position. Missing, duplicate, malformed, or over-budget scope metadata must stay fail-closed.
assert "depth >= PROOF_OPERATOR_SCOPE_DEPTH_LIMIT" in scope_collect
assert "Ast::Decl.Scoped(nested, position)" in scope_collect
assert "proof_operator_scope_body_mask(nested, source_work)" in scope_collect
assert "proof_source_operator_dunder_mask(name)" in scope_body
assert 'receiver_is_self <- receiver_type == "Self"' in scope_body
assert "explicit_receiver_mask <- explicit_receiver_mask | operator_mask" in scope_body
assert "global_mask <- global_mask | explicit_receiver_mask | operator_mask" in scope_body
assert "global_mask <- global_mask | operator_mask if not receiver_is_self and not receiver_type_known" in scope_body
assert "global_mask <- global_mask | proof_source_operator_dunder_mask(name)" in scope_body
assert "proof_operator_scope_hash(row.line, row.offset)" in scope_index_build
assert "bucket_size: usize = bucket_sizes[slot] + 1" in scope_index_build
assert "bucket_size > PROOF_OPERATOR_SCOPE_MAX_BUCKET" in scope_index_build
scope_build_call = builder.index("proof_operator_scope_index_build(report.source.source_declarations, source_work)")
scope_mask_call = builder.index("proof_operator_scope_index_mask_at(scope_index_status.index, implementation.line, implementation.offset, source_work)")
scope_mask_set = builder.index("implementation.operator_mask <- scope_mask.mask")
impl_index_valid = builder.rindex("report.analysis_1.operator_impls.valid <- true")
assert scope_build_call < scope_mask_call < scope_mask_set < impl_index_valid
assert "scope.explicit_receiver_type != implementation.concrete" in builder
assert "scope.global_operator_mask" in builder
assert "impl_scope.explicit_receiver_mask if not impl_scope.implementation_scope" in builder
assert "impl_scope.operator_mask if not impl_scope.implementation_scope" in builder
assert "operator_mask: PROOF_SOURCE_OPERATOR_ALL_FLAGS" in builder
assert "line: concrete_annotation.line" in builder and "offset: concrete_annotation.offset" in builder
assert "line: scope_annotation.line" in builder and "offset: scope_annotation.offset" in builder
assert "return (false, false, count, PROOF_SOURCE_OPERATOR_ALL_FLAGS) if not index.valid" in scope_lookup
assert "count != index.hashes.count or count != index.next_indices.count" in scope_lookup
assert "return (true, false, count, PROOF_SOURCE_OPERATOR_ALL_FLAGS) if found" in scope_lookup
assert "index.hashes[entry] == hash and row.line == line and row.offset == offset" in scope_lookup
assert "entry < count or visits > count" in scope_lookup
assert "return (true, found, found_index, mask)" in scope_lookup
assert "report.analysis_1.operator_impls.global_operator_mask <- 0" in report_reset
assert report_reset.index("operator_impls.global_operator_mask <- 0") < report_reset.index("operator_impls.valid <- false")

# Pairing scans and hash-chain allocation/search share explicit work accounting;
# overlong collision chains refuse the source instead of falling back to a scan.
assert "proof_report_source_work_charge(1, source_work)" in builder
assert "PROOF_OPERATOR_IMPL_MAX_BUCKET: usize = 64" in (ROOT / "src/proof/check/operator_impl_index_build.elisa").read_text(encoding="utf-8")
assert "bucket_size: usize = bucket_sizes[slot] + 1" in builder
assert "bucket_size > PROOF_OPERATOR_IMPL_MAX_BUCKET" in builder
assert "proof_report_source_work_charge(sview_len(implementation.concrete), source_work)" in builder
assert "proof_report_source_work_charge(sview_len(implementation.protocol), source_work)" in builder
assert "annotation_index + 1 >= report.source.source_annotations.count" in builder
assert 'paired_concrete.owner != "__impl_concrete"' in builder
assert "annotation_index == 0" in builder
assert 'scope_annotation.owner != "__impl_scope"' in builder
assert "scope_annotation.line != concrete_annotation.line" in builder
assert "for scope_annotation in report.source.source_annotations" not in builder
for invariant in (
    "count != report.analysis_1.operator_impls.hashes.count",
    "count != report.analysis_1.operator_impls.next_indices.count",
    "return (false, false) if entry > count",
    "next_entry != count and next_entry >= entry",
    "return (false, false) if entry < count or visits > count",
    "proof_type_audit_work_charge(1, source_work)",
):
    assert invariant in query, invariant

# The current type-wide dunder query already catches every implementation candidate, including
# legacy `Less` impls. Keep the kernel admission path to one metered lookup per receiver type.
assert "proof_report_builtin_operator_impl_exists_with_work(report, concrete, protocol, source_work)" in kernel_query
assert 'proof_report_builtin_operator_impl_exists_with_work(report, concrete, "Less", source_work)' not in kernel_query

# The annotation-only compatibility path must use the same strict adjacent parser pair and fail
# closed on malformed rows instead of reviving the old same-line nested scan.
assert "annotation_index + 1 >= annotations.count" in annotation_lookup
assert 'paired_concrete.owner != "__impl_concrete"' in annotation_lookup
assert "annotation_index == 0" in annotation_lookup
assert 'scope.owner != "__impl_scope"' in annotation_lookup
assert "for scope in annotations" not in annotation_lookup

print("operator impl index: build ordering, bounded lookup, and malformed-chain refusal guarded")
