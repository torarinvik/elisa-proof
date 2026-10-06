# Part 1b of the test matrix, sourced after the shared setup. Stable agent-facing proof state must
# expose the checked kernel, replay status, trust boundary,
# and action protocol in a structured, internally consistent report.
run_json_report "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["source"]["bytes"] > 0; assert report["source"]["fingerprint"]["algorithm"] == "fnv1a32"; assert 0 <= report["source"]["fingerprint"]["value"] < 2**32; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert len(report["certificates"]) == report["replay"]["certificates"]; assert report["repair_queue"] == []; assert report["trust"]["trusted_assumptions"] == []; assert report["trust"]["trusted_boundary_facts"] == len(report["trust"]["boundary_facts"]); assert all(set(fact) == {"kind", "owner", "line", "kernel_root"} for fact in report["trust"]["boundary_facts"]); assert report["replay"]["gaps"] == 0; assert all(not goal["proven"] or goal["replay_status"] == "replayed" for goal in report["goals"]); assert report["kernel"]["format"] == "elisa-proof-kernel-v1"; assert report["kernel"]["independent_replay"] is True; assert len(report["kernel"]["nodes"]) > 0; assert report["action_protocol"]["format"] == "elisa-proof-tactics-v1"; assert report["action_protocol"]["admission"] == "kernel-backed"; assert report["action_protocol"]["operations"] == ["assumption", "exact", "decide", "intro", "apply", "simp", "have", "instantiate", "rewrite", "split", "left", "right", "cases"]; assert report["action_protocol"]["branch_script"]["nested"] is True; assert report["action_protocol"]["branch_script"]["max_branch_depth"] == 32'
run_json_report "$ROOT_DIR/examples/branch_return_proof_accounting.elisa" | python3 -c 'import json, sys; r=json.load(sys.stdin); assert r["status"] == "proved" and r["verification_state"] == "proved"; assert r["summary"]["proven"] == r["summary"]["obligations"]; assert r["replay"]["certificates"] == r["replay"]["replayed"] and r["replay"]["gaps"] == 0; assert len(r["goals"]) > r["summary"]["obligations"]; assert all(d["verified"] for d in r["declaration_details"] if d["kind"] == "function")'
json_probe_status=$?
if [[ "$json_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: JSON report is not a valid structured proof state\n' >&2
    exit 1
fi

# A quantified tactic result is accepted only after both its tactic trace and proof certificate
# replay. The adjacent negative case ensures wrapped integer bounds cannot justify vacuity.
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_quantifier.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["tactic"]["valid"] is True; assert report["tactic"]["solved"] is True; assert report["tactic"]["kernel_trace_replayed"] is True; assert report["tactic"]["kernel_replayed"] is True; assert report["tactic"]["certificate_replayed"] is True'
quantifier_tactic_probe_status=${PIPESTATUS[1]}
if [[ "$quantifier_tactic_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: portable quantifier tactic was not independently replayed\n' >&2
    exit 1
fi
"$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/tactic_script_rejected_ambiguous_range_quantifier.json" "$ROOT_DIR/examples/verified.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["tactic"]["valid"] is False; assert report["tactic"]["solved"] is False; assert report["tactic"]["kernel_replayed"] is False' && ambiguous_range_quantifier_status=0 || ambiguous_range_quantifier_status=${PIPESTATUS[1]}
if [[ "$ambiguous_range_quantifier_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a quantifier over an ambiguous range bound was admitted\n' >&2
    exit 1
fi

# Reject malformed-size tactic input before recording any partially admitted actions.
for rejected_tactic_fixture in tactic_script_rejected_large_line tactic_script_rejected_large_expr_line; do
    rejected_tactic_report="$standalone_probe_dir/$rejected_tactic_fixture.json"
    "$ROOT_DIR/build/elisa-proof" --tactics "$ROOT_DIR/examples/$rejected_tactic_fixture.json" "$ROOT_DIR/examples/verified.elisa" >"$rejected_tactic_report"
    rejected_tactic_status=$?
    if [[ "$rejected_tactic_status" -ne 1 ]]; then
        printf 'proof test matrix failed: overflowing JSON line was accepted for %s\n' "$rejected_tactic_fixture" >&2
        exit 1
    fi
    python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert report["tactic"]["valid"] is False; assert report["tactic"]["action_count"] == 0' "$rejected_tactic_report"
    rejected_tactic_probe_status=$?
    if [[ "$rejected_tactic_probe_status" -ne 0 ]]; then
        printf 'proof test matrix failed: overflowing JSON line report was incomplete for %s\n' "$rejected_tactic_fixture" >&2
        exit 1
    fi
done
oversized_action_script="$standalone_probe_dir/tactic-script-oversized-actions.json"
python3 - "$oversized_action_script" <<'PY'
import json
import sys

script = {
    "format": "elisa-proof-tactics-v1",
    "initial": {"facts": [], "goal": {"kind": "bool", "value": True}},
    "actions": [{"action": "unknown"}] * 65537,
}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(script, handle)
PY
"$ROOT_DIR/build/elisa-proof" --tactics "$oversized_action_script" "$ROOT_DIR/examples/verified.elisa" >"$standalone_probe_dir/tactic-script-oversized-actions-report.json"
oversized_action_status=$?
if [[ "$oversized_action_status" -ne 1 ]]; then
    printf 'proof test matrix failed: oversized tactic action array was accepted\n' >&2
    exit 1
fi
python3 -c 'import json, sys; report=json.load(open(sys.argv[1])); assert report["status"] == "failed"; assert report["tactic"]["valid"] is False; assert report["tactic"]["action_count"] == 0' "$standalone_probe_dir/tactic-script-oversized-actions-report.json"
oversized_action_probe_status=$?
if [[ "$oversized_action_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: oversized tactic action report was incomplete\n' >&2
    exit 1
fi
