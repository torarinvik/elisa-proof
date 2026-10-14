# shellcheck shell=bash
# Focused source-span regression for the type-bound local result-consumer adapter.
run_json_report "$ROOT_DIR/examples/type_bound_local_multiline_return.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert any(goal["rule"] == "goal" and goal["proven"] and any(origin and origin["kind"] == "type-bound" for origin in goal["fact_origins"]) for goal in report["goals"])'
type_bound_local_multiline_return_probe_status=${PIPESTATUS[1]}
if [[ "$type_bound_local_multiline_return_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: multiline explicit return source binding\n' >&2
    exit 1
fi
