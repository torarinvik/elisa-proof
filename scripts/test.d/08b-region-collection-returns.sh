# Sourced by scripts/test.sh after 08a: caller-region collection returns must not escape.
set +e
run_json_report "$ROOT_DIR/examples/rejected_local_darray_return.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; errors = [(d["kind_code"], d["name"]) for d in report.get("semantic_diagnostics", []) if d["severity"] == 1]; assert errors == [(596, "local_values")], errors; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert {f["kind"] for f in report["findings"]} >= {"ensure-unproven", "function-summary-unverified"}; declarations = {d["name"]: d for d in report["declaration_details"] if d["kind"] == "function"}; assert not declarations["rejected_local_darray_return"]["verified"] and not declarations["main"]["verified"]; assert declarations["rejected_local_darray_return"]["verification_reason"] == "source-error" and declarations["main"]["verification_reason"] == "source-error"; assert all(not g["proven"] or g.get("replay_status") == "replayed" for g in report["goals"]), report["goals"]'
rejected_local_darray_return_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_local_darray_return_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a moved inferred-region collection escaped its function\n' >&2
    exit 1
fi
