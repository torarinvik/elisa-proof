# shellcheck shell=bash
# Adversarial regression for conditional conversion recognition in the proof checker.
# Sourced after test part 6; never run alone.

# A user-defined method named like a builtin conversion stays an ordinary call when a return is
# split into conditional arms. Its summary may not be replaced by numeric-conversion semantics.
set +e
run_json_report "$ROOT_DIR/examples/rejected_shadowed_conversion_conditional.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] != "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert any(finding["name"] == "shadowed_method_is_not_a_conversion" for finding in report["findings"])'
shadowed_conversion_status=${PIPESTATUS[1]}
set -e
if [[ "$shadowed_conversion_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a method shadowing a numeric conversion was admitted as a conversion\n' >&2
    exit 1
fi
