# shellcheck shell=bash
# Enum variants are resolved by their owning enum identity. Repeated names must work both as
# context-sensitive shorthand and through an explicit qualified enum path. Distinct tags of one
# enum are disjoint, while repeating the exact assumed tag must not prove its negation.
set +e
run_json_report "$ROOT_DIR/examples/enum_variant_resolution.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "proved"; assert r["summary"]["semantic_errors"] == 0; assert r["summary"]["proven"] == r["summary"]["obligations"]; assert r["replay"]["certificates"] == r["replay"]["replayed"] > 0 and r["replay"]["gaps"] == 0; assert not any(f["kind"] == "contract-proposition-type" for f in r["findings"]); ds={d["name"]:d for d in r["declaration_details"] if d["kind"]=="function"}; assert all(ds[n]["verified"] for n in ("enum_shorthand_context", "enum_qualified_context", "enum_variant_tags_are_disjoint"))'
enum_variant_resolution_status=${PIPESTATUS[1]}
set -e
if [[ "$enum_variant_resolution_status" -ne 0 ]]; then
    printf 'proof test matrix failed: owner-aware enum variant resolution\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_enum_variant_disjoint.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "failed"; assert r["summary"]["semantic_errors"] == 0; assert r["replay"]["gaps"] == 0; assert any(f["kind"] == "ensure-unproven" and f["name"] == "rejected_same_enum_variant_negation" for f in r["findings"]); d=next(d for d in r["declaration_details"] if d["name"] == "rejected_same_enum_variant_negation"); assert not d["verified"]'
enum_variant_disjoint_rejection_status=${PIPESTATUS[1]}
set -e
if [[ "$enum_variant_disjoint_rejection_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an enum tag was incorrectly treated as disjoint from itself\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_enum_variant_result.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "failed"; assert r["summary"]["semantic_errors"] == 0; assert r["replay"]["certificates"] == r["replay"]["replayed"] and r["replay"]["gaps"] == 0; assert not any(f["kind"] == "contract-proposition-type" for f in r["findings"]); assert any(f["kind"] == "ensure-unproven" and f["name"] == "rejected_enum_variant_result" for f in r["findings"]); d=next(d for d in r["declaration_details"] if d["name"] == "rejected_enum_variant_result"); assert not d["verified"]'
enum_variant_rejection_status=${PIPESTATUS[1]}
set -e
if [[ "$enum_variant_rejection_status" -ne 0 ]]; then
    printf 'proof test matrix failed: false enum contract was admitted\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/signed_literal_comparison.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "proved"; assert r["summary"]["semantic_errors"] == 0; assert r["summary"]["proven"] == r["summary"]["obligations"]; assert r["replay"]["certificates"] == r["replay"]["replayed"] > 0 and r["replay"]["gaps"] == 0; d=next(d for d in r["declaration_details"] if d["name"] == "signed_literal_comparison"); assert d["verified"]'
signed_literal_comparison_status=${PIPESTATUS[1]}
set -e
if [[ "$signed_literal_comparison_status" -ne 0 ]]; then
    printf 'proof test matrix failed: signed-literal comparison\n' >&2
    exit 1
fi

set +e
run_json_report "$ROOT_DIR/examples/rejected_signed_literal_comparison.elisa" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "failed"; assert r["summary"]["semantic_errors"] == 0; assert r["replay"]["gaps"] == 0; assert any(f["kind"] == "ensure-unproven" and f["name"] == "rejected_signed_literal_comparison" for f in r["findings"]); d=next(d for d in r["declaration_details"] if d["name"] == "rejected_signed_literal_comparison"); assert not d["verified"]'
rejected_signed_literal_comparison_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_signed_literal_comparison_status" -ne 0 ]]; then
    printf 'proof test matrix failed: rejected signed-literal comparison\n' >&2
    exit 1
fi

