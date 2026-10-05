# shellcheck shell=bash
# Narrow propositional reasoning over float comparisons must replay, while stale facts and source
# overloads remain outside the supported fragment.
float_boolean_report="$standalone_probe_dir/float-boolean-guard.json"
run_json_report "$ROOT_DIR/examples/float_boolean_guard.elisa" >"$float_boolean_report"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "proved" and r["findings"] == []; assert all(g["proven"] for g in r["goals"] if g["rule"] == "goal"); assert all(c["replayed"] for c in r["certificates"]); assert next(d for d in r["declaration_details"] if d["name"] == "float_boolean_guard")["verified"]' "$float_boolean_report"
for float_probe in rejected_float_boolean_stale_fact rejected_float_boolean_overloaded; do
    report="$standalone_probe_dir/$float_probe.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$float_probe.elisa" >"$report"
    probe_status=$?
    set -e
    if [[ "$probe_status" -ne 1 ]]; then
        printf 'proof test matrix failed: unsupported float proposition accepted: %s\n' "$float_probe" >&2
        exit 1
    fi
    python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["summary"]["semantic_errors"] == 0; assert not any(g["name"].startswith("rejected_float_boolean_") and g["proven"] and g["rule"] == "goal" for g in r["goals"])' "$report"
done
