# Pattern elimination and algebraic/record constructor encoding regressions.
run_json_report "$ROOT_DIR/examples/pattern_scalar_literals.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "char" for node in report["kernel"]["nodes"])'
pattern_scalar_literals_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_scalar_literals_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: scalar literal pattern facts\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pinned_pattern.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] and goal["rule"] == "goal" for goal in report["goals"])'
pinned_pattern_probe_status=${PIPESTATUS[1]}
if [[ "$pinned_pattern_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: pinned-pattern equality fact\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/pattern_or.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["failed"] == 0; assert report["replay"]["gaps"] == 0; assert any(goal["proven"] and goal["rule"] == "goal" for goal in report["goals"])'
pattern_or_probe_status=${PIPESTATUS[1]}
if [[ "$pattern_or_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: closed OR-pattern branch fact\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/shorthand_member.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "shorthand" and node["name"] == "None" for node in report["kernel"]["nodes"])'
shorthand_member_probe_status=${PIPESTATUS[1]}
if [[ "$shorthand_member_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: const-enum shorthand was not encoded as a replayed kernel atom\n' >&2
    exit 1
fi
run_json_report "$ROOT_DIR/examples/constructor_kernel.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert "construct" in kinds; assert "record-update" in kinds; assert "field-init" in kinds'
constructor_kernel_probe_status=${PIPESTATUS[1]}
if [[ "$constructor_kernel_probe_status" -ne 0 ]]; then
    printf 'proof test matrix failed: constructor/update terms were not encoded for independent replay\n' >&2
    exit 1
fi
