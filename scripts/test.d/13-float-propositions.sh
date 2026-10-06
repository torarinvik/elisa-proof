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
    python3 -c 'import json,sys; name=sys.argv[2]; r=json.load(open(sys.argv[1])); expected="call-requires-unproven" if name.endswith("stale_fact") else "expression-unsupported"; assert r["summary"]["semantic_errors"] == 0; assert any(f["name"] == name and f["kind"] == expected for f in r["findings"]); assert not any(g["name"] == name and g["proven"] and g["rule"] == "goal" for g in r["goals"])' "$report" "$float_probe"
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
# Adversarial review of the float fragment: NaN reflexivity outside float mode, literal spelling,
# signed zero, f32 rounding, closed literal arithmetic, negated order, user struct operators, and
# facts made stale by a loop write. Each contract is false under IEEE and must stay unproven.
for float_probe in rejected_float_local_nan_reflexivity rejected_float_literal_spelling_disequality \
    rejected_float_signed_zero rejected_float_literal_rounding rejected_float_closed_literal_comparison \
    rejected_float_negated_order rejected_float_struct_operator rejected_float_stale_after_loop; do
    report="$standalone_probe_dir/$float_probe.json"
    set +e
    run_json_report "$ROOT_DIR/examples/$float_probe.elisa" >"$report"
    probe_status=$?
    set -e
    if [[ "$probe_status" -ne 1 ]]; then
        printf 'proof test matrix failed: IEEE-false float contract accepted: %s\n' "$float_probe" >&2
        exit 1
    fi
    python3 -c 'import json,sys; name=sys.argv[2]; r=json.load(open(sys.argv[1])); assert r["status"] == "failed" and r["summary"]["semantic_errors"] == 0; assert any(f["name"] == name for f in r["findings"]); assert not any(g["name"] == name and g["proven"] and g["rule"] == "goal" for g in r["goals"]); assert all(c["replayed"] for c in r["certificates"])' "$report" "$float_probe"
done
# Forged packages must not use the opaque literal token to replay IEEE-false laws.
run_py_test test_float_literal_forgery.py
