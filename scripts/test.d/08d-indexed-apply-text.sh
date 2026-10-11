# Sourced after the JSON indexed-apply regression: the text facade must preserve its index.
cat > "$proof_render_dir/indexed_apply_text.proof" <<'PROOF'
# goal 1
proof unrelated_open_obligation_1:
    by apply 2147483647
qed
PROOF

set +e
"$ROOT_DIR/build/elisa-proof" --script "$proof_render_dir/indexed_apply_text.proof" "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/indexed_apply_text.json"
indexed_apply_text_status=$?
set -e
if [[ "$indexed_apply_text_status" -ne 1 ]]; then
    printf 'proof test matrix failed: indexed apply text should parse and report its rejected out-of-range fact (status=%s)\n' "$indexed_apply_text_status" >&2
    exit 1
fi
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

with open(os.path.join(sys.argv[1], "indexed_apply_text.json"), encoding="utf-8") as handle:
    report = json.load(handle)
step = report["tactic"]["trace"][0]
assert step["action"] == "apply"
assert step["has_argument_index"] is True and step["argument_index"] == 2147483647
assert step["accepted"] is False
assert report["source_goal_binding"]["bound"]
PY

# The parser must not merge an action name with its argument, or silently let a later header
# retarget actions to a different source goal.
cat > "$proof_render_dir/indexed_apply_missing_separator.proof" <<'PROOF'
# goal 1
proof p:
    by apply1
qed
PROOF
cat > "$proof_render_dir/indexed_apply_duplicate_header.proof" <<'PROOF'
# goal 1
# goal 2
proof p:
    by assumption
qed
PROOF
cat > "$proof_render_dir/indexed_apply_bad_declaration.proof" <<'PROOF'
# goal 1
proof by assumption
    by apply 2147483647
qed
PROOF
for invalid_script in indexed_apply_missing_separator indexed_apply_duplicate_header indexed_apply_bad_declaration; do
    set +e
    "$ROOT_DIR/build/elisa-proof" --script "$proof_render_dir/$invalid_script.proof" "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/$invalid_script.json"
    invalid_script_status=$?
    set -e
    if [[ "$invalid_script_status" -ne 1 ]]; then
        printf 'proof test matrix failed: malformed indexed apply script should be refused (name=%s status=%s)\n' "$invalid_script" "$invalid_script_status" >&2
        exit 1
    fi
done
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

for name in ("indexed_apply_missing_separator", "indexed_apply_duplicate_header", "indexed_apply_bad_declaration"):
    with open(os.path.join(sys.argv[1], name + ".json"), encoding="utf-8") as handle:
        report = json.load(handle)
    assert report["tactic"]["valid"] is False, name
    assert report["tactic"]["action_count"] == 0, name
    assert report["tactic"]["trace"] == [], name
PY
