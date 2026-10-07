# shellcheck shell=bash
# Call stability, ownership, borrow, capability and region replay regressions.
# A fact over a by-value scalar the body never lets escape survives an opaque call, and a
# conjunctive guard entails each of its parts. Both are needed to re-establish a bounded-recursion
# precondition at a second call; each conjunct is a derived fact the kernel re-proves.
set +e
run_json_report "$ROOT_DIR/examples/call_stable_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"survives_state_writing_call", "survives_second_call", "survives_branch_join", "survives_call_guard", "survives_returning_branch"} <= names; origins = {origin["kind"] for goal in report["goals"] for origin in goal["fact_origins"] if origin}; assert "branch-conjunct" in origins'
call_stable_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$call_stable_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: call-stable facts and branch conjuncts\n' >&2
    exit 1
fi
# The boundary of those two rules: a scalar the callee can write, a scalar a branch assigns, and a
# disjunction are all refused. Nothing here may be proven.
set +e
run_json_report "$ROOT_DIR/examples/rejected_call_stable_facts.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; refused = {"aliased_scalar", "assigned_in_branch", "disjunctive_branch", "negated_conjunctive_guard", "rebound_after_guard"}; assert refused <= {finding["name"] for finding in report["findings"]}; claimed = {goal["name"] for goal in report["goals"] if goal["proven"] and goal["rule"] != "resource-safety" and goal["name"] in refused and "depth <= 127" in str(goal)}; assert not claimed'
rejected_call_stable_facts_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_call_stable_facts_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a fact survived a call or a branch that could falsify it\n' >&2
    exit 1
fi

# Rebound call-result facts survive only while their owning local remains unreachable; a mutable
# lend to that local still invalidates the summary.
set +e
run_json_report "$ROOT_DIR/examples/call_stable_result_symbols.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {item["name"]: item for item in report["declaration_details"] if item["kind"] == "function"}; assert functions["result_bound_survives_unrelated_call"]["verified"]; assert not functions["result_bound_does_not_survive_mutable_lend"]["verified"]; assert not [finding for finding in report["findings"] if finding["name"] == "result_bound_survives_unrelated_call"]; assert any(finding["name"] == "result_bound_does_not_survive_mutable_lend" and finding["kind"] == "ensure-unproven" for finding in report["findings"]); assert not report["trust"]["trusted_assumptions"]'
call_stable_result_symbols_status=${PIPESTATUS[1]}
set -e
if [[ "$call_stable_result_symbols_status" -ne 0 ]]; then
    printf 'proof test matrix failed: rebound call-result stability or mutable-lend refusal\n' >&2
    exit 1
fi

# A by-value aggregate that contains a reference still reaches external state. Its nested
# collection extent must be forgotten across a call that can mutate the referent through a global.
set +e
run_json_report "$ROOT_DIR/examples/rejected_nested_shared_extent_global.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unsupported"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {item["name"]: item for item in report["declaration_details"] if item["kind"] == "function"}; assert not functions["nested_shared_extent_must_not_survive"]["verified"]; assert any(item["kind"] == "index-upper-unproven" and item["name"] == "nested_shared_extent_must_not_survive" and item["status"] == "unknown" for item in report["findings"]); assert not any(goal["name"] == "nested_shared_extent_must_not_survive" and goal["rule"] == "index-upper" and goal["proven"] for goal in report["goals"])'
rejected_nested_shared_extent_global_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_nested_shared_extent_global_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a by-value aggregate reference preserved a mutable pointee extent across a call\n' >&2
    exit 1
fi

# A view-bearing aggregate is borrowed storage too, even though `view[T]` is not itself a
# reference field. Refuse to preserve even a nested field fact through a call until that alias
# shape can be modeled path-sensitively.
set +e
run_json_report "$ROOT_DIR/examples/rejected_borrowed_view_call_stability.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["verification_state"] == "unknown"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; functions = {item["name"]: item for item in report["declaration_details"] if item["kind"] == "function"}; assert not functions["borrowed_view_root_must_not_preserve_nested_facts"]["verified"]; assert any(item["kind"] == "ensure-unproven" and item["name"] == "borrowed_view_root_must_not_preserve_nested_facts" and item["status"] == "unknown" for item in report["findings"]); assert not any(goal["name"] == "borrowed_view_root_must_not_preserve_nested_facts" and goal["rule"] != "resource-safety" and goal["proven"] for goal in report["goals"])'
rejected_borrowed_view_call_stability_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_borrowed_view_call_stability_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a view-bearing aggregate was trusted as call-local storage\n' >&2
    exit 1
fi

# A call that lends only shared references cannot change the caller's resource state, so it is
# admitted from the callee's declared modes with no body summary. That is the only path open to a
# recursive component, which can never consume one of its own summaries.
set +e
run_json_report "$ROOT_DIR/examples/shared_borrow_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; kinds = {node["kind"] for node in nodes}; assert "resource-call-lend" in kinds; shared = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert all(node["left"] == 0 and node["children_count"] == node["auxiliary"] * 2 for node in shared); formals = [nodes[child] for node in shared for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]; assert formals; assert all(formal["kind"] == "resource-call-formal" for formal in formals); assert all(formal["operator"] in ("value", "external-shared") for formal in formals); assert any(formal["operator"] == "external-shared" for formal in formals)'
shared_borrow_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$shared_borrow_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: shared-reference calls\n' >&2
    exit 1
fi

# A capability the callee may write through, one that outlives the call, and one the caller no
# longer holds all still require the callee's own converged summary.
set +e
run_json_report "$ROOT_DIR/examples/rejected_shared_borrow_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "recursive_reference_return") in findings; assert ("resource-use-after-move", "lends_moved_value") in findings; assert ("borrow-call-opaque", "lends_shared_while_mutably_borrowed") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_shared_borrow_calls_status=${PIPESTATUS[1]}
set -e
# An exclusive lend needs no callee summary either: the callee can do no more than write through
# the reference, so the caller over-approximates the call by a write to the whole lent place. Every
# exclusive capability must be one the caller holds alone.
set +e
run_json_report "$ROOT_DIR/examples/writable_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; lends = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert lends; formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["children_count"]]]; assert any(formal["operator"] == "external-mutable" for formal in formals); assert any(formal["operator"] == "external-shared" for formal in formals)'
writable_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$writable_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: confined writable lending\n' >&2
    exit 1
fi

# Signature types resolve across every block of a module, so an `extend` block's recursive
# shared walk returning a sibling-declared scalar struct is a confined lend, while a sibling
# struct that holds a reference still requires the callee's converged summary.
set +e
run_json_report "$ROOT_DIR/examples/module_extend_shared_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["gaps"] == 0; assert any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
module_extend_lend_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_module_extend_shared_lend.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "extend_escape") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_module_extend_lend_status=${PIPESTATUS[1]}
set -e
if [[ "$module_extend_lend_status" -ne 0 || "$rejected_module_extend_lend_status" -ne 0 ]]; then
    printf 'proof test matrix failed: module extend lend types\n' >&2
    exit 1
fi

# A module constant passed by value is spelled by its module path in the resource trace, which
# replay admits as static. A bare constant is qualified by the producer, also from an `extend`
# block; a local that shadows it stays a bare binding.
set +e
run_json_report "$ROOT_DIR/examples/replay_qualified_constant_argument.elisa" | python3 -c '
import json, sys
report = json.load(sys.stdin)
assert report["status"] == "proved" and report["replay"]["gaps"] == 0
nodes = report["kernel"]["nodes"]
def spell(index):
    node = nodes[index]
    if node["kind"] == "scope":
        return spell(node["left"]) + "::" + node["name"]
    return node["name"] if node["kind"] == "ident" else node["kind"]
spelled = [spell(node["left"]) for node in nodes if node["kind"] == "resource-call-arg" and node["name"] == "remaining"]
assert spelled == ["binary", "Limits::DEPTH", "QualifiedArgument::LOCAL_DEPTH", "absent::ROOT_DEPTH", "LOCAL_DEPTH", "QualifiedArgument::LOCAL_DEPTH"], spelled
nested = [node for node in nodes if node["kind"] == "resource-call-arg" and node["name"] == "value" and node["left"] < len(nodes)]
def contains_qualified_constant(root):
    node = nodes[root]
    if node["kind"] == "scope":
        return spell(root) == "absent::SIGNED_DEPTH" or contains_qualified_constant(node["left"])
    if node["kind"] == "unary" or node["kind"] == "paren":
        return node["left"] < len(nodes) and contains_qualified_constant(node["left"])
    if node["kind"] == "binary":
        return node["left"] < len(nodes) and contains_qualified_constant(node["left"]) or node["right"] < len(nodes) and contains_qualified_constant(node["right"])
    return False
assert any(nodes[node["left"]]["kind"] == "unary" and contains_qualified_constant(node["left"]) for node in nested), nested
def contains_bare_shadow(root):
    node = nodes[root]
    if node["kind"] == "ident":
        return node["name"] == "SIGNED_DEPTH"
    if node["kind"] == "unary" or node["kind"] == "paren":
        return node["left"] < len(nodes) and contains_bare_shadow(node["left"])
    if node["kind"] == "binary":
        return node["left"] < len(nodes) and contains_bare_shadow(node["left"]) or node["right"] < len(nodes) and contains_bare_shadow(node["right"])
    return False
assert any(nodes[node["left"]]["kind"] == "unary" and contains_bare_shadow(node["left"]) for node in nested), nested
region_shadow = [node for node in nested if nodes[node["left"]]["kind"] == "binary" and nodes[nodes[node["left"]]["left"]]["kind"] == "ident" and nodes[nodes[node["left"]]["left"]]["name"] == "REGION_DEPTH"]
assert region_shadow, nested
'
qualified_constant_status=${PIPESTATUS[1]}
set -e
if [[ "$qualified_constant_status" -ne 0 ]]; then
    printf 'proof test matrix failed: static constant spelling in resource traces\n' >&2
    exit 1
fi

# A region-derived scalar and a moved aggregate both shadow same-spelled root constants. The
# former stays a bare local in a nested value expression; the latter remains a local field place
# and is rejected after move, never rewritten as the static root constant.
set +e
run_json_report "$ROOT_DIR/examples/rejected_moved_qualified_constant_shadow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert report["replay"]["gaps"] == 0; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert ("resource-use-after-move", "moved_shadow_caller") in {(finding["kind"], finding["name"]) for finding in report["findings"]}; nodes = report["kernel"]["nodes"]; args = [node for node in nodes if node["kind"] == "resource-call-arg" and node["name"] == "value"]; assert any(nodes[node["left"]]["kind"] == "binary" and nodes[nodes[node["left"]]["left"]]["kind"] == "field" and nodes[nodes[nodes[node["left"]]["left"]]["left"]]["kind"] == "ident" and nodes[nodes[nodes[node["left"]]["left"]]["left"]]["name"] == "SIGNED_DEPTH" for node in args), args'
moved_qualified_shadow_status=${PIPESTATUS[1]}
set -e
if [[ "$moved_qualified_shadow_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a moved local shadow was qualified as a static constant\n' >&2
    exit 1
fi

# Two exclusive capabilities over one place, a shared one beside an exclusive one, and an
# exclusive lend across a live borrow are each refused with no event recorded. The pinned
# frontend also reports the two call-site overlaps; the proof checker must refuse all three on
# its own, including the live-borrow case the frontend does not see.
set +e
run_json_report "$ROOT_DIR/examples/rejected_writable_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert sorted((diagnostic["line"], diagnostic["actual"]) for diagnostic in report["semantic_diagnostics"]) == [(16, "swap_pair"), (35, "read_and_write")]; assert report["replay"]["gaps"] == 0; findings = {(finding["kind"], finding["name"]) for finding in report["findings"]}; assert ("borrow-call-opaque", "swap_pair") in findings; assert ("borrow-call-opaque", "read_and_write") in findings; assert ("borrow-call-opaque", "touch_borrowed") in findings; assert not any(node["kind"] == "resource-call-lend" for node in report["kernel"]["nodes"])'
rejected_writable_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$rejected_writable_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: an unconfined exclusive lend was admitted\n' >&2
    exit 1
fi

# A lifetime parameter does not stop a call from being a lend: the callee may allocate into a
# mapped caller region and can never close one. Every formal lifetime must be pinned to a region
# active at the call, and every region-carrying actual must land on a formal declaring it.
set +e
run_json_report "$ROOT_DIR/examples/region_lend_calls.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; nodes = report["kernel"]["nodes"]; children = report["kernel"]["children"]; lends = [node for node in nodes if node["kind"] == "resource-call-lend"]; assert lends; assert all(node["children_count"] == node["auxiliary"] * 2 + node["right"] for node in lends); assert any(node["right"] == 2 for node in lends); maps = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"] * 2:node["children_start"] + node["children_count"]]]; assert maps; assert all(entry["kind"] == "resource-call-region" and entry["operator"] == "param" and entry["name"] and entry["secondary_name"] for entry in maps); formals = [nodes[child] for node in lends for child in children[node["children_start"] + node["auxiliary"]:node["children_start"] + node["auxiliary"] * 2]]; assert any(formal["secondary_name"] for formal in formals)'
region_lend_calls_status=${PIPESTATUS[1]}
set -e
if [[ "$region_lend_calls_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic lending\n' >&2
    exit 1
fi

# A region-polymorphic callee that does have a converged summary must compose into its caller. A
# construction's left edge is the constructed type, not a value; a record update's left edge is
# the base record and still is one.
set +e
run_json_report "$ROOT_DIR/examples/region_call_summary.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; kinds = {node["kind"] for node in report["kernel"]["nodes"]}; assert {"resource-region-alloc", "construct", "record-update", "resource-call"} <= kinds'
region_call_summary_status=${PIPESTATUS[1]}
set -e
if [[ "$region_call_summary_status" -ne 0 ]]; then
    printf 'proof test matrix failed: region-polymorphic callee summary composition\n' >&2
    exit 1
fi

# A branch condition may carry an executable call wherever that call runs whenever the condition
# is evaluated, not only at the root. A call that may be skipped stays refused.
set +e
run_json_report "$ROOT_DIR/examples/condition_call_positions.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["summary"]["proven"] == report["summary"]["obligations"]; assert report["findings"] == []; assert report["replay"]["certificates"] == report["replay"]["replayed"]; assert report["replay"]["gaps"] == 0; names = {goal["name"] for goal in report["goals"] if goal["proven"]}; assert {"bare_call", "negated_call", "compared_call", "short_circuit_left", "arithmetic_call", "guarded_index"} <= names'
condition_call_positions_status=${PIPESTATUS[1]}
set -e
if [[ "$condition_call_positions_status" -ne 0 ]]; then
    printf 'proof test matrix failed: executable calls in branch conditions\n' >&2
    exit 1
fi

# A range loop binder is a scalar copy, not a borrow of the outer binding it shadows; a
# collection binder that shadows a local borrow is still refused in a contract.
set +e
run_json_report "$ROOT_DIR/examples/range_binder_shadow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "proved"; assert report["summary"]["semantic_errors"] == 0; assert report["findings"] == []; assert report["replay"]["gaps"] == 0'
range_binder_shadow_status=${PIPESTATUS[1]}
run_json_report "$ROOT_DIR/examples/rejected_collection_binder_shadow.elisa" | python3 -c 'import json, sys; report = json.load(sys.stdin); assert report["status"] == "failed"; assert report["summary"]["semantic_errors"] == 0; assert ("borrow-contract-unsupported", 5) in {(f["kind"], f["line"]) for f in report["findings"]}'
collection_binder_shadow_status=${PIPESTATUS[1]}
set -e
if [[ "$range_binder_shadow_status" -ne 0 || "$collection_binder_shadow_status" -ne 0 ]]; then
    printf 'proof test matrix failed: a range loop binder was read as a borrow, or a collection binder was not\n' >&2
    exit 1
fi
