# shellcheck shell=bash
# Narrow propositional reasoning over float comparisons must replay, while stale facts and source
# overloads remain outside the supported fragment.
float_boolean_report="$standalone_probe_dir/float-boolean-guard.json"
run_json_report "$ROOT_DIR/examples/float_boolean_guard.elisa" >"$float_boolean_report"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "proved" and r["findings"] == []; assert all(g["proven"] for g in r["goals"] if g["rule"] == "goal"); assert all(c["replayed"] for c in r["certificates"]); assert next(d for d in r["declaration_details"] if d["name"] == "float_boolean_guard")["verified"]' "$float_boolean_report"
literal_guard_report="$standalone_probe_dir/float-literal-guard.json"
run_json_report "$ROOT_DIR/examples/float_literal_guard.elisa" >"$literal_guard_report"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == "proved" and r["findings"] == []; assert all(g["proven"] for g in r["goals"] if g["rule"] == "goal"); assert all(c["replayed"] for c in r["certificates"]); assert next(d for d in r["declaration_details"] if d["name"] == "float_literal_guard")["verified"]' "$literal_guard_report"
for float_probe in rejected_float_boolean_stale_fact rejected_float_boolean_overloaded rejected_float_literal_stale_fact; do
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
for float_probe in rejected_float_arithmetic_atom rejected_float_order_totality; do
    report="$standalone_probe_dir/$float_probe.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$float_probe.elisa" >"$report"
    probe_status=$?
    set -e
    if [[ "$probe_status" -ne 1 ]]; then
        printf 'proof test matrix failed: unsupported float law accepted: %s\n' "$float_probe" >&2
        exit 1
    fi
    python3 -c 'import json,sys; name=sys.argv[2]; r=json.load(open(sys.argv[1])); assert r["status"] == "failed"; assert not any(g["name"] == name and g["proven"] and g["rule"] == "goal" for g in r["goals"]); assert all(c["replayed"] for c in r["certificates"])' "$report" "$float_probe"
done
