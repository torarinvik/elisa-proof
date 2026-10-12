# Sourced after the JSON indexed-apply regression: the text facade must preserve its index.
cat > "$proof_render_dir/indexed_apply_text.proof" <<'PROOF'
# source: fingerprint fnv1a32=970611481, complete=false, admissible=true
# goal 1 of 4, rule goal, in repair_compound_equality at line 7
proof p:
    by apply 2147483647
qed
PROOF

set +e
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --script "$proof_render_dir/indexed_apply_text.proof" "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/indexed_apply_text.json"
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
step = report["state"]["trace"][0]
assert step["action"] == "apply"
assert step["has_argument_index"] is True and step["argument_index"] == 2147483647
assert step["accepted"] is False
assert report["source_goal_binding"]["bound"]
assert report["source"]["fingerprint_match"] is True
PY

# Canonical proof output carries a source fingerprint. Preserve it through text elaboration so
# a stale script cannot silently target a different obligation after the source changes.
cat > "$proof_render_dir/indexed_apply_stale_source.proof" <<'PROOF'
# source: fingerprint fnv1a32=970611482, complete=false, admissible=true
# goal 1 of 4, rule goal, in repair_compound_equality at line 7
proof p:
    by apply 2147483647
qed
PROOF
set +e
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --script "$proof_render_dir/indexed_apply_stale_source.proof" "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/indexed_apply_stale_source.json"
stale_source_status=$?
set -e
if [[ "$stale_source_status" -ne 1 ]]; then
    printf 'proof test matrix failed: stale text proof source fingerprint should be refused (status=%s)\n' "$stale_source_status" >&2
    exit 1
fi
python3 - "$proof_render_dir/indexed_apply_stale_source.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["source"]["fingerprint_match"] is False
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
cat > "$proof_render_dir/indexed_apply_duplicate_source_fingerprint.proof" <<'PROOF'
# source: fingerprint fnv1a32=970611481, complete=false, admissible=true
# source: fingerprint fnv1a32=970611481, complete=false, admissible=true
# goal 1
proof p:
    by apply 2147483647
qed
PROOF
for invalid_script in indexed_apply_missing_separator indexed_apply_duplicate_header indexed_apply_bad_declaration indexed_apply_duplicate_source_fingerprint; do
    set +e
    "${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --script "$proof_render_dir/$invalid_script.proof" "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/$invalid_script.json"
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

for name in ("indexed_apply_missing_separator", "indexed_apply_duplicate_header", "indexed_apply_bad_declaration", "indexed_apply_duplicate_source_fingerprint"):
    with open(os.path.join(sys.argv[1], name + ".json"), encoding="utf-8") as handle:
        report = json.load(handle)
    assert report["tactic"]["valid"] is False, name
    assert report["tactic"]["action_count"] == 0, name
    assert report["state"]["trace"] == [], name
PY
