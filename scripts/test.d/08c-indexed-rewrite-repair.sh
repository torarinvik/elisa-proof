# Sourced after the repair batch and region-return checks: a generated equality rewrite records
# its selected source fact and the text script remains runnable through the checked tactic path.

set +e
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --repair 1 "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/indexed_repair.json"
indexed_repair_status=$?
set -e
if [[ "$indexed_repair_status" -ne 0 ]]; then
    printf 'proof test matrix failed: --repair did not derive a rewrite from an equality hypothesis\n' >&2
    exit 1
fi

python3 - "$proof_render_dir" <<'PY'
import json
import os
import re
import sys

directory = sys.argv[1]
with open(os.path.join(directory, "indexed_repair.json"), encoding="utf-8") as handle:
    report = json.load(handle)
assert report["status"] == "repaired" and report["search"]["candidates"] >= report["search"]["tried"]
assert report["search"]["exhaustive"] is False
script = report["script"]
match = re.search(r"^\s*by (rewriteback|rewrite) ([0-9]+)\s*$", script, re.MULTILINE)
assert match, script
with open(os.path.join(directory, "indexed_repair.proof"), "w", encoding="utf-8") as handle:
    handle.write(script)

actions = []
for line in script.splitlines():
    step = re.match(r"^\s*by ([a-z]+)(?: ([0-9]+))?\s*$", line)
    if not step:
        continue
    action = {"action": step.group(1)}
    if step.group(2):
        action["argument_index"] = int(step.group(2))
    actions.append(action)
assert actions and actions[0]["action"] in ("rewrite", "rewriteback")
bad_actions = [dict(action) for action in actions]
bad_actions[0]["argument_index"] = 2147483647
with open(os.path.join(directory, "indexed_rewrite_bad_index.json"), "w", encoding="utf-8") as handle:
    json.dump({"format": "elisa-proof-tactics-v1", "target": {"goal_id": 1, "goal_fingerprint": 2903951783}, "actions": bad_actions}, handle)
PY

set +e
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --script "$proof_render_dir/indexed_repair.proof" "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/indexed_repair_rerun.json"
indexed_repair_rerun_status=$?
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --tactics "$proof_render_dir/indexed_rewrite_bad_index.json" "$ROOT_DIR/examples/tactic_repair_target.elisa" > "$proof_render_dir/indexed_rewrite_bad_index_result.json"
indexed_rewrite_bad_index_status=$?
set -e
if [[ "$indexed_repair_rerun_status" -ne 0 ]]; then
    printf 'proof test matrix failed: generated indexed rewrite did not re-check\n' >&2
    exit 1
fi

set +e
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

directory = sys.argv[1]
def load(name):
    with open(os.path.join(directory, name), encoding="utf-8") as handle:
        return json.load(handle)

rerun = load("indexed_repair_rerun.json")
assert rerun["status"] == "proved"
assert rerun["tactic"]["solved"] and rerun["tactic"]["trace_replayed"] and rerun["tactic"]["kernel_trace_replayed"]
assert rerun["tactic"]["kernel_replayed"] and rerun["tactic"]["certificate_replayed"]
rewrite = next(step for step in rerun["tactic"]["trace"] if step["action"] == "rewrite")
assert rewrite["has_argument_index"] and rewrite["has_argument"] and rewrite["has_secondary"]
bad = load("indexed_rewrite_bad_index_result.json")
assert bad["status"] == "failed"
assert bad["tactic"]["solved"] is False
assert bad["tactic"]["valid"] is False
PY
indexed_rewrite_shape_status=$?
set -e
if [[ "$indexed_rewrite_shape_status" -ne 0 || "$indexed_rewrite_bad_index_status" -ne 1 ]]; then
    printf 'proof test matrix failed: indexed rewrite replay did not preserve or reject its selected fact (shape=%s status=%s)\n' "$indexed_rewrite_shape_status" "$indexed_rewrite_bad_index_status" >&2
    exit 1
fi

# A second in-range equality must not be substituted for the equality selected by the script.
set +e
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --repair 1 "$ROOT_DIR/examples/tactic_repair_two_equalities.elisa" > "$proof_render_dir/two_equalities_repair.json"
two_equalities_repair_status=$?
set -e
if [[ "$two_equalities_repair_status" -ne 0 ]]; then
    printf 'proof test matrix failed: repair did not use the relevant equality in a two-equality context\n' >&2
    exit 1
fi
python3 - "$proof_render_dir" <<'PY'
import json
import os
import re
import sys

directory = sys.argv[1]
with open(os.path.join(directory, "two_equalities_repair.json"), encoding="utf-8") as handle:
    report = json.load(handle)
match = re.search(r"^\s*by (?:rewriteback|rewrite) ([0-9]+)\s*$", report["script"], re.MULTILINE)
assert report["status"] == "repaired" and match
with open(os.path.join(directory, "two_equalities_repair.proof"), "w", encoding="utf-8") as handle:
    handle.write(report["script"])
PY
set +e
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --script "$proof_render_dir/two_equalities_repair.proof" "$ROOT_DIR/examples/tactic_repair_two_equalities.elisa" > "$proof_render_dir/two_equalities_rerun.json"
two_equalities_rerun_status=$?
set -e
if [[ "$two_equalities_rerun_status" -ne 0 ]]; then
    printf 'proof test matrix failed: two-equality generated repair did not re-check\n' >&2
    exit 1
fi
python3 - "$proof_render_dir" <<'PY'
import json
import os
import re
import sys

directory = sys.argv[1]
def load(name):
    with open(os.path.join(directory, name), encoding="utf-8") as handle:
        return json.load(handle)

repair = load("two_equalities_repair.json")
rerun = load("two_equalities_rerun.json")
selected = int(re.search(r"^\s*by (?:rewriteback|rewrite) ([0-9]+)\s*$", repair["script"], re.MULTILINE).group(1))
facts = rerun["tactic"]["initial_facts"]
alternatives = [index for index, fact in enumerate(facts) if index != selected and fact.get("kind") == "binary" and fact.get("operator") == "=="]
assert alternatives, facts
wrong_index = alternatives[0]
actions = []
for line in repair["script"].splitlines():
    step = re.match(r"^\s*by ([a-z]+)(?: ([0-9]+))?\s*$", line)
    if not step:
        continue
    action = {"action": step.group(1)}
    if step.group(2):
        action["argument_index"] = int(step.group(2))
    actions.append(action)
actions[0]["argument_index"] = wrong_index
with open(os.path.join(directory, "two_equalities_wrong_fact.json"), "w", encoding="utf-8") as handle:
    json.dump({"format": "elisa-proof-tactics-v1", "target": {"goal_id": 1}, "actions": actions}, handle)
PY
set +e
"${ELISA_PROOF_BIN:-$ROOT_DIR/build/elisa-proof}" --tactics "$proof_render_dir/two_equalities_wrong_fact.json" "$ROOT_DIR/examples/tactic_repair_two_equalities.elisa" > "$proof_render_dir/two_equalities_wrong_fact_result.json"
two_equalities_wrong_fact_status=$?
set -e
set +e
python3 - "$proof_render_dir" <<'PY'
import json
import os
import sys

with open(os.path.join(sys.argv[1], "two_equalities_wrong_fact_result.json"), encoding="utf-8") as handle:
    report = json.load(handle)
rewrite = next(step for step in report["tactic"]["trace"] if step["action"] == "rewrite")
assert report["status"] == "failed" and not report["tactic"]["solved"]
assert rewrite["has_argument_index"] and not rewrite["accepted"]
PY
two_equalities_wrong_fact_shape_status=$?
set -e
if [[ "$two_equalities_wrong_fact_status" -ne 1 || "$two_equalities_wrong_fact_shape_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a different valid equality index was not refused (status=%s shape=%s)\n' "$two_equalities_wrong_fact_status" "$two_equalities_wrong_fact_shape_status" >&2
    exit 1
fi
