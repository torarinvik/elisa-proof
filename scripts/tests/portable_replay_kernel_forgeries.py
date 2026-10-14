"""Adversarial semantic and kernel replay cases for portable packages.

Loaded by the single portable-replay test entry after positive exports have been checked. The
provided namespace supplies real exported packages and common package/replay helpers.
"""
import copy

from portable_replay_support import *

# Substitution for a finite outer quantifier must not capture the free `y` in its range
# when descending through an inner `forall y`. A naive textual substitution turns
# `forall x in [y], forall y in [0], x == y` into a tautology, although the original is
# false when the free integer y is 1. The replay substitution deliberately declines this
# nested-binder shape until it has a capture-avoiding representation.
nested_capture = copy.deepcopy(quantified)
nested_capture["kernel"] = {"nodes": [], "children": []}

def collection(package, kind, elements):
    start = len(package["kernel"]["children"])
    package["kernel"]["children"].extend(elements)
    return append_node(package, kind, children_start=start, children_count=len(elements))

def marker_call(package, marker, arguments):
    callee = append_node(package, "ident", name=marker)
    start = len(package["kernel"]["children"])
    for argument in arguments:
        package["kernel"]["children"].append(append_node(package, "call_arg", left=argument))
    return append_node(package, "call", left=callee, children_start=start, children_count=len(arguments))

free_y = append_node(nested_capture, "ident", name="y")
outer_values = collection(nested_capture, "array", [free_y])
inner_zero = append_node(nested_capture, "int", value="0")
inner_values = collection(nested_capture, "array", [inner_zero])
bound_x = append_node(nested_capture, "ident", name="x")
bound_y = append_node(nested_capture, "ident", name="y")
inner_body = append_node(nested_capture, "binary", "==", bound_x, bound_y)
inner_forall = append_node(nested_capture, "quantifier", "forall", inner_values, inner_body,
                           name="y", auxiliary=1)
nested_forall = append_node(nested_capture, "quantifier", "forall", outer_values, inner_forall,
                           name="x", auxiliary=1)
scalar_y = marker_call(nested_capture, "__elisa_primitive_scalar_type", [free_y])
nested_theorem = {
    "goal_id": 0, "name": "nested-binder-capture", "line": 1, "rule": "quantifier-forall",
    "hypotheses": [scalar_y], "hypothesis_origins": [{"kind": "forged"}],
    "conclusion": nested_forall, "statement": "", "goal_fingerprint": 0,
}
nested_capture["theorems"] = [reseal(nested_capture, nested_theorem)]
refused(nested_capture, "nested-quantifier-capture", "rejected", "kernel-rejected")

# Dictionary key/value binders are substituted simultaneously. In `forall k, v in {v: 0},
# k == v`, the `v` in the dictionary key is free and distinct from the value binder. With
# hypothesis v == 1, the proposition is false (1 != 0). Sequentially substituting k -> v
# and then v -> 0 would capture the inserted free key and turn it into 0 == 0.
dict_capture = copy.deepcopy(quantified)
dict_capture["kernel"] = {"nodes": [], "children": []}
free_v = append_node(dict_capture, "ident", name="v")
dict_zero = append_node(dict_capture, "int", value="0")
dict_one = append_node(dict_capture, "int", value="1")
dict_entry = append_node(dict_capture, "dict_entry", left=free_v, right=dict_zero)
dict_values = collection(dict_capture, "dict", [dict_entry])
key_var = append_node(dict_capture, "ident", name="k")
value_var = append_node(dict_capture, "ident", name="v")
dict_body = append_node(dict_capture, "binary", "==", key_var, value_var)
dict_forall = append_node(dict_capture, "quantifier", "forall", dict_values, dict_body,
                          name="k", auxiliary=2, secondary_name="v")
scalar_free_v = marker_call(dict_capture, "__elisa_primitive_scalar_type", [free_v])
free_v_is_one = append_node(dict_capture, "binary", "==", free_v, dict_one)
dict_theorem = {
    "goal_id": 0, "name": "dictionary-binder-capture", "line": 1, "rule": "quantifier-forall",
    "hypotheses": [scalar_free_v, free_v_is_one],
    "hypothesis_origins": [{"kind": "forged"}, {"kind": "forged"}],
    "conclusion": dict_forall, "statement": "", "goal_fingerprint": 0,
}
dict_capture["theorems"] = [reseal(dict_capture, dict_theorem)]
refused(dict_capture, "dictionary-quantifier-capture", "rejected", "kernel-rejected")

# Positive control: under the same v == 1 hypothesis and dictionary, k != v is true.
# This confirms the forged sequent above reaches quantifier replay with a usable free scalar.
dict_control = copy.deepcopy(dict_capture)
not_equal_body = append_node(dict_control, "binary", "!=", key_var, value_var)
not_equal_forall = append_node(dict_control, "quantifier", "forall", dict_values, not_equal_body,
                               name="k", auxiliary=2, secondary_name="v")
dict_control_theorem = {
    "goal_id": 0, "name": "dictionary-binder-capture-control", "line": 1,
    "rule": "quantifier-forall", "hypotheses": [scalar_free_v, free_v_is_one],
    "hypothesis_origins": [{"kind": "forged"}, {"kind": "forged"}],
    "conclusion": not_equal_forall, "statement": "", "goal_fingerprint": 0,
}
dict_control["theorems"] = [reseal(dict_control, dict_control_theorem)]
control_code, control_result = replay(dict_control, "dictionary-quantifier-capture-control")
assert control_code == 0 and control_result["status"] == "replayed", control_result

# Raw dictionary AST children can retain pairs that runtime construction overwrites when a
# later equal key appears. Existential replay over both rows could use the stale first value.
# Forbid that forged range before evaluating its body, while keeping the single-key form useful.
dict_exists = copy.deepcopy(quantified)
dict_exists["kernel"] = {"nodes": [], "children": []}
wrapped_key_left = append_node(dict_exists, "int", value="255")
wrapped_key_right = append_node(dict_exists, "int", value="1")
dict_key_a = append_node(dict_exists, "binary", "+", wrapped_key_left, wrapped_key_right)
dict_key_b = append_node(dict_exists, "int", value="0")
dict_value_zero = append_node(dict_exists, "int", value="0")
dict_value_one = append_node(dict_exists, "int", value="1")
dict_entry_a = append_node(dict_exists, "dict_entry", left=dict_key_a, right=dict_value_zero)
dict_entry_b = append_node(dict_exists, "dict_entry", left=dict_key_b, right=dict_value_one)
dict_range = collection(dict_exists, "dict", [dict_entry_a, dict_entry_b])
exists_key = append_node(dict_exists, "ident", name="k")
exists_value = append_node(dict_exists, "ident", name="v")
mathematical_key = append_node(dict_exists, "int", value="256")
key_is_wrapped_value = append_node(dict_exists, "binary", "==", exists_key, mathematical_key)
value_is_zero = append_node(dict_exists, "binary", "==", exists_value, dict_value_zero)
exists_body = append_node(dict_exists, "binary", "and", key_is_wrapped_value, value_is_zero)
duplicate_exists = append_node(dict_exists, "quantifier", "exists", dict_range, exists_body,
                               name="k", auxiliary=2, secondary_name="v")
duplicate_exists_theorem = {
    "goal_id": 0, "name": "wrapping-key-existential", "line": 1,
    "rule": "quantifier-exists", "hypotheses": [], "hypothesis_origins": [],
    "conclusion": duplicate_exists, "statement": "", "goal_fingerprint": 0,
}
dict_exists["theorems"] = [reseal(dict_exists, duplicate_exists_theorem)]
refused(dict_exists, "wrapping-key-existential", "rejected", "kernel-rejected")

dict_single = copy.deepcopy(dict_exists)
dict_single["kernel"] = {"nodes": [], "children": []}
single_key = append_node(dict_single, "int", value="1")
single_value = append_node(dict_single, "int", value="0")
single_entry = append_node(dict_single, "dict_entry", left=single_key, right=single_value)
single_range = collection(dict_single, "dict", [single_entry])
single_bound_key = append_node(dict_single, "ident", name="k")
single_bound_value = append_node(dict_single, "ident", name="v")
single_key_match = append_node(dict_single, "binary", "==", single_bound_key, single_key)
single_value_match = append_node(dict_single, "binary", "==", single_bound_value, single_value)
single_body = append_node(dict_single, "binary", "and", single_key_match, single_value_match)
single_exists = append_node(dict_single, "quantifier", "exists", single_range, single_body,
                            name="k", auxiliary=2, secondary_name="v")
single_exists_theorem = {
    "goal_id": 0, "name": "single-key-existential-control", "line": 1,
    "rule": "quantifier-exists", "hypotheses": [], "hypothesis_origins": [],
    "conclusion": single_exists, "statement": "", "goal_fingerprint": 0,
}
dict_single["theorems"] = [reseal(dict_single, single_exists_theorem)]
single_code, single_result = replay(dict_single, "single-key-existential-control")
assert single_code == 0 and single_result["status"] == "replayed", single_result

# Typed integer literals may prove uniqueness only when both the bits and integer sort match.
typed_dict_exists = copy.deepcopy(quantified)
typed_dict_exists["kernel"] = {"nodes": [], "children": []}
typed_key_a = append_node(typed_dict_exists, "typed-int", value="1", name="i64")
typed_key_b = append_node(typed_dict_exists, "typed-int", value="1", name="i64")
typed_value_zero = append_node(typed_dict_exists, "typed-int", value="0", name="i64")
typed_value_one = append_node(typed_dict_exists, "typed-int", value="1", name="i64")
typed_entry_a = append_node(typed_dict_exists, "dict_entry", left=typed_key_a, right=typed_value_zero)
typed_entry_b = append_node(typed_dict_exists, "dict_entry", left=typed_key_b, right=typed_value_one)
typed_range = collection(typed_dict_exists, "dict", [typed_entry_a, typed_entry_b])
typed_bound_key = append_node(typed_dict_exists, "ident", name="typed_k")
typed_bound_value = append_node(typed_dict_exists, "ident", name="typed_v")
typed_key_match = append_node(typed_dict_exists, "binary", "==", typed_bound_key, typed_key_a)
typed_value_match = append_node(typed_dict_exists, "binary", "==", typed_bound_value, typed_value_zero)
typed_body = append_node(typed_dict_exists, "binary", "and", typed_key_match, typed_value_match)
typed_duplicate_exists = append_node(typed_dict_exists, "quantifier", "exists", typed_range, typed_body,
                                    name="typed_k", auxiliary=2, secondary_name="typed_v")
typed_duplicate_theorem = {
    "goal_id": 0, "name": "typed-duplicate-key-existential", "line": 1,
    "rule": "quantifier-exists", "hypotheses": [], "hypothesis_origins": [],
    "conclusion": typed_duplicate_exists, "statement": "", "goal_fingerprint": 0,
}
typed_dict_exists["theorems"] = [reseal(typed_dict_exists, typed_duplicate_theorem)]
refused(typed_dict_exists, "typed-duplicate-key-existential", "rejected", "kernel-rejected")

typed_dict_unique = copy.deepcopy(typed_dict_exists)
typed_dict_unique["kernel"] = {"nodes": [], "children": []}
typed_key_a = append_node(typed_dict_unique, "typed-int", value="1", name="i64")
typed_key_b = append_node(typed_dict_unique, "typed-int", value="2", name="i64")
typed_value_zero = append_node(typed_dict_unique, "typed-int", value="0", name="i64")
typed_value_one = append_node(typed_dict_unique, "typed-int", value="1", name="i64")
typed_entry_a = append_node(typed_dict_unique, "dict_entry", left=typed_key_a, right=typed_value_zero)
typed_entry_b = append_node(typed_dict_unique, "dict_entry", left=typed_key_b, right=typed_value_one)
typed_range = collection(typed_dict_unique, "dict", [typed_entry_a, typed_entry_b])
typed_bound_key = append_node(typed_dict_unique, "ident", name="typed_k")
typed_bound_value = append_node(typed_dict_unique, "ident", name="typed_v")
typed_key_match = append_node(typed_dict_unique, "binary", "==", typed_bound_key, typed_key_a)
typed_value_match = append_node(typed_dict_unique, "binary", "==", typed_bound_value, typed_value_zero)
typed_body = append_node(typed_dict_unique, "binary", "and", typed_key_match, typed_value_match)
typed_unique_exists = append_node(typed_dict_unique, "quantifier", "exists", typed_range, typed_body,
                                  name="typed_k", auxiliary=2, secondary_name="typed_v")
typed_unique_theorem = {
    "goal_id": 0, "name": "typed-unique-key-existential-control", "line": 1,
    "rule": "quantifier-exists", "hypotheses": [], "hypothesis_origins": [],
    "conclusion": typed_unique_exists, "statement": "", "goal_fingerprint": 0,
}
typed_dict_unique["theorems"] = [reseal(typed_dict_unique, typed_unique_theorem)]
typed_unique_code, typed_unique_result = replay(typed_dict_unique, "typed-unique-key-existential-control")
assert typed_unique_code == 0 and typed_unique_result["status"] == "replayed", typed_unique_result

base = packages["verified"]
# A recognized type marker is a domain restriction when used as a premise; it is not
# an automatically true proposition. Keep this source-neutral sequent from proving an
# unsigned marker as a consequence of an unrelated signed-width marker, even when hidden
# inside a larger Boolean goal.
marker_goal = copy.deepcopy(base)
marker_goal["kernel"] = {"nodes": [], "children": []}
marker_subject = append_node(marker_goal, "ident", name="x")
marker_width = append_node(marker_goal, "int", value="8")
signed_bound = marker_call(marker_goal, "__elisa_signed_type_bound", [marker_subject, marker_width])
unsigned_bound = marker_call(marker_goal, "__elisa_unsigned_type_bound", [marker_subject, marker_width])
marker_one = append_node(marker_goal, "int", value="1")
marker_zero = append_node(marker_goal, "int", value="0")
subject_is_one = append_node(marker_goal, "binary", "==", marker_subject, marker_one)
subject_is_zero = append_node(marker_goal, "binary", "==", marker_subject, marker_zero)
forged_disjunction = append_node(marker_goal, "binary", "or", unsigned_bound, subject_is_zero)
marker_theorem = {
    "goal_id": 0, "name": "type-marker-is-not-a-proposition", "line": 1,
    "rule": "goal", "hypotheses": [signed_bound, subject_is_one],
    "hypothesis_origins": [{"kind": "forged"}, {"kind": "forged"}], "conclusion": forged_disjunction,
    "statement": "", "goal_fingerprint": 0,
}
marker_goal["theorems"] = [reseal(marker_goal, marker_theorem)]
refused(marker_goal, "type-marker-goal-not-tautological", "rejected", "kernel-rejected")

assumption = next(t for t in base["theorems"] if t["rule"] == "goal" and t["conclusion"] in t["hypotheses"])
code, result = replay(with_theorem(base, assumption), "assumption")
assert code == 0, result

# Exact compound excluded middle is checked by the portable kernel, not a
# producer truth flag. Reseal a false near-match so identity checks cannot hide it.
excluded = copy.deepcopy(base)
excluded["kernel"] = {"nodes": [], "children": []}
subject = append_node(excluded, "ident", name="c")
scalar = marker_call(excluded, "__elisa_primitive_scalar_type", [subject])
values = [append_node(excluded, "int", value=str(value)) for value in (32, 9, 14)]
atoms = [append_node(excluded, "binary", "==", subject, value) for value in values]
predicate = append_node(excluded, "binary", "or", atoms[0], atoms[1])
different = append_node(excluded, "binary", "or", atoms[0], atoms[2])
negated = append_node(excluded, "unary", "not", predicate)
conclusion = append_node(excluded, "binary", "or", predicate, negated)
claim = copy.deepcopy(assumption)
claim.update(hypotheses=[scalar], hypothesis_origins=[{"kind": "forged"}], conclusion=conclusion)
excluded["theorems"] = [reseal(excluded, claim)]
code, result = replay(excluded, "compound-excluded-middle")
assert code == 0 and result["status"] == "replayed", result
near_match = copy.deepcopy(excluded)
near_match["kernel"]["nodes"][negated]["left"] = different
near_match["theorems"] = [reseal(near_match, near_match["theorems"][0])]
refused(near_match, "compound-not-complement", "rejected", "kernel-rejected")
double_negative = copy.deepcopy(excluded)
twice_negated = append_node(double_negative, "unary", "not", negated)
double_negative["theorems"][0]["conclusion"] = append_node(double_negative, "binary", "or", predicate, twice_negated)
double_negative["theorems"] = [reseal(double_negative, double_negative["theorems"][0])]
refused(double_negative, "compound-double-negation-is-not-complement", "rejected", "kernel-rejected")

# Consistent forgeries: the kernel itself must refuse them.
closed = copy.deepcopy(packages["closed_goal_width_uniform"])
closed_nodes = closed["kernel"]["nodes"]
closed_claim = next(theorem for theorem in closed["theorems"]
                    if closed_nodes[theorem["conclusion"]]["kind"] == "binary"
                    and closed_nodes[theorem["conclusion"]]["operator"] == "or"
                    and closed_nodes[closed_nodes[closed_nodes[theorem["conclusion"]]["left"]]["left"]]["kind"] == "binary"
                    and closed_nodes[closed_nodes[closed_nodes[theorem["conclusion"]]["left"]]["left"]]["operator"] == "-")
comparison = closed_nodes[closed_nodes[closed_claim["conclusion"]]["left"]]
assert comparison["operator"] == "<", comparison
ring = closed_nodes[comparison["left"]]
assert closed_nodes[ring["left"]]["value"] == "0" and closed_nodes[ring["right"]]["value"] == "1", ring
comparison["operator"] = ">"
closed["theorems"] = [reseal(closed, closed_claim)]
refused(closed, "closed-width-nonuniform-claim", "rejected", "kernel-rejected")

wrapped_denial = copy.deepcopy(base)
wrapped_denial["kernel"] = {"nodes": [], "children": []}
subject = append_node(wrapped_denial, "ident", name="x")
width = append_node(wrapped_denial, "int", value="8")
scalar = marker_call(wrapped_denial, "__elisa_primitive_scalar_type", [subject])
signed = marker_call(wrapped_denial, "__elisa_signed_type_bound", [subject, width])
zero = append_node(wrapped_denial, "int", value="0")
one = append_node(wrapped_denial, "int", value="1")
low = append_node(wrapped_denial, "int", value="126")
high = append_node(wrapped_denial, "int", value="127")
magnitude = append_node(wrapped_denial, "int", value="128")
minimum = append_node(wrapped_denial, "unary", "-", magnitude)
increment = append_node(wrapped_denial, "binary", "+", subject, one)
lower = append_node(wrapped_denial, "binary", ">=", subject, low)
upper = append_node(wrapped_denial, "binary", "<=", subject, high)
premise = append_node(wrapped_denial, "binary", "!=", increment, zero)
claim = copy.deepcopy(assumption)
claim.update(hypotheses=[scalar, signed, lower, upper, premise],
             hypothesis_origins=[{"kind": "adapter"}] * 5,
             conclusion=append_node(wrapped_denial, "binary", "!=", subject, zero))
wrapped_denial["theorems"] = [reseal(wrapped_denial, claim)]
code, result = replay(wrapped_denial, "linear-denial-wrapped-premise-control")
assert code == 0 and result["status"] == "replayed", result
false_wrapped = copy.deepcopy(wrapped_denial)
false_wrapped["theorems"][0]["conclusion"] = append_node(false_wrapped, "binary", "!=", increment, minimum)
false_wrapped["theorems"] = [reseal(false_wrapped, false_wrapped["theorems"][0])]
refused(false_wrapped, "linear-denial-wrapping-goal", "rejected", "kernel-rejected")

indexed = copy.deepcopy(packages["disjunctive_goals"])
indexed_claim = next(t for t in indexed["theorems"] if t["name"] == "live" and t["rule"] == "goal")
indexed_nodes = indexed["kernel"]["nodes"]
element_witnesses = [h for h in indexed_claim["hypotheses"]
                     if indexed_nodes[h]["kind"] == "call"
                     and indexed_nodes[indexed_nodes[h]["left"]]["name"] == "__elisa_primitive_scalar_element"]
assert len(element_witnesses) == 1, element_witnesses
indexed_claim["hypotheses"] = [h for h in indexed_claim["hypotheses"] if h not in element_witnesses]
indexed["theorems"] = [reseal(indexed, indexed_claim)]
refused(indexed, "indexed-denial-without-element-witness", "rejected", "kernel-rejected")

clamped = copy.deepcopy(packages["goal_disjunct_split_probe"])
clamp_claim = next(t for t in clamped["theorems"] if t["name"] == "a" and t["rule"] == "goal")
clamp_nodes = clamped["kernel"]["nodes"]
# Remove the lower bound that refutes the low-speed alternative. Keep the
# statement and fingerprint consistent, so rejection must come from replay.
removed = [h for h in clamp_claim["hypotheses"]
           if clamp_nodes[h]["kind"] == "binary" and clamp_nodes[h]["operator"] == ">="]
assert len(removed) == 1, removed
clamp_claim["hypotheses"] = [h for h in clamp_claim["hypotheses"] if h not in removed]
clamped["theorems"] = [reseal(clamped, clamp_claim)]
refused(clamped, "clamp-call-without-lower-bound", "rejected", "kernel-rejected")

dropped = copy.deepcopy(assumption)
dropped["hypotheses"] = [h for h in dropped["hypotheses"] if h != dropped["conclusion"]]
forged = with_theorem(base, dropped)
refused(with_theorem(base, reseal(forged, forged["theorems"][0])), "dropped-hypothesis", "rejected", "kernel-rejected")

false_goal = copy.deepcopy(base)
one = append_node(false_goal, "int", value="1")
two = append_node(false_goal, "int", value="2")
wrong = append_node(false_goal, "binary", "<", two, one)
right = append_node(false_goal, "binary", "<", one, two)
claim = copy.deepcopy(assumption)
claim["conclusion"] = wrong
false_goal["theorems"] = [reseal(false_goal, claim)]
refused(false_goal, "false-conclusion", "rejected", "kernel-rejected")
control = copy.deepcopy(false_goal)
control["theorems"][0]["conclusion"] = right
reseal(control, control["theorems"][0])
assert replay(control, "true-conclusion")[0] == 0

# The independent kernel must not capture a source-supplied `_1` when generalizing the second
# field place. Without checking every generated marker for availability, these consistent facts
# become contradictory only after `b.y` is replaced by the existing `__elisa_field_place_1`,
# allowing the false goal `a.x == b.y` to pass by explosion.
field_collision = copy.deepcopy(base)
field_collision["kernel"] = {"nodes": [], "children": []}

def named(kind, name, operator="", left=0, right=0, value="0"):
    return append_node(field_collision, kind, operator, left, right, value, name)

def call(marker, arguments):
    callee = named("ident", marker)
    start = len(field_collision["kernel"]["children"])
    for argument in arguments:
        field_collision["kernel"]["children"].append(
            named("call_arg", "", left=argument)
        )
    return append_node(field_collision, "call", left=callee, children_start=start,
                       children_count=len(arguments))

def binary(operator, left, right):
    return append_node(field_collision, "binary", operator, left, right)

a_x = named("field", "x", left=named("ident", "a"))
b_y = named("field", "y", left=named("ident", "b"))
marker_one = named("ident", "__elisa_field_place_1")
zero = append_node(field_collision, "int", value="0")
one = append_node(field_collision, "int", value="1")
eq_text = named("string", "Eq")
hypotheses = [
    binary("==", a_x, zero),
    binary("==", b_y, one),
    binary("==", marker_one, zero),
    call("__elisa_primitive_scalar_type", [a_x]),
    call("__elisa_primitive_scalar_type", [b_y]),
    call("__elisa_primitive_scalar_type", [marker_one]),
    call("__elisa_builtin_operator_type", [a_x, eq_text]),
    call("__elisa_builtin_operator_type", [b_y, eq_text]),
    call("__elisa_builtin_operator_type", [marker_one, eq_text]),
]
collision_claim = {
    "goal_id": 0,
    "name": "field-place-marker-capture",
    "line": 1,
    "rule": "goal",
    "hypotheses": hypotheses,
    "hypothesis_origins": [{"kind": "forged"}] * len(hypotheses),
    "conclusion": binary("==", a_x, b_y),
    "statement": "",
    "goal_fingerprint": 0,
}
field_collision["theorems"] = [reseal(field_collision, collision_claim)]
refused(field_collision, "field-place-marker-capture", "rejected", "kernel-rejected")

relabeled = copy.deepcopy(assumption)
relabeled["rule"] = "resource-safety"
refused(with_theorem(base, relabeled), "wrong-rule", "rejected", "kernel-rejected")
unknown = copy.deepcopy(assumption)
unknown["rule"] = "trust-me"
refused(with_theorem(base, unknown), "unknown-rule", "rejected", "unknown-rule")

# Inconsistent forgeries: the statement and fingerprint bind the sequent that was checked.
mismatch = copy.deepcopy(assumption)
mismatch["statement"] = mismatch["statement"].replace("x", "y", 1)
refused(with_theorem(base, mismatch), "statement-mismatch", "rejected", "statement-mismatch")
fingerprint = copy.deepcopy(assumption)
fingerprint["goal_fingerprint"] = (fingerprint["goal_fingerprint"] + 1) % 2**32
refused(with_theorem(base, fingerprint), "fingerprint-mismatch", "rejected", "fingerprint-mismatch")
out_of_range = copy.deepcopy(assumption)
out_of_range["conclusion"] = len(base["kernel"]["nodes"])
refused(with_theorem(base, out_of_range), "root-out-of-range", "rejected", "root-out-of-range")

# Forged arenas: unknown kinds, bad child ranges, cycles and forward references.
unknown_kind = copy.deepcopy(base)
unknown_kind["kernel"]["nodes"][assumption["conclusion"]]["kind"] = "oracle"
refused(with_theorem(unknown_kind, assumption), "unknown-kind", "malformed", "arena-inadmissible")
bad_children = copy.deepcopy(base)
call = next(i for i, n in enumerate(bad_children["kernel"]["nodes"]) if n["kind"] == "call")
bad_children["kernel"]["nodes"][call]["children_count"] = len(bad_children["kernel"]["children"]) + 1
refused(with_theorem(bad_children, assumption), "bad-children", "malformed", "arena-inadmissible")
for name, left in (("cycle", None), ("forward", "next")):
    cyclic = copy.deepcopy(base)
    root = assumption["conclusion"]
    cyclic["kernel"]["nodes"][root]["left"] = root if left is None else len(cyclic["kernel"]["nodes"]) - 1
    if left is not None:
        assert len(cyclic["kernel"]["nodes"]) - 1 > root
    refused(with_theorem(cyclic, assumption), name, "malformed", "arena-inadmissible")

# An exponential DAG is linear in the arena but not in its identity: the budget stops it.
dag = copy.deepcopy(base)
dag["kernel"] = {"nodes": [], "children": []}
top = append_node(dag, "int", value="1")
for _ in range(40):
    top = append_node(dag, "binary", "+", top, top)
goal = append_node(dag, "binary", "==", top, top)
dag["theorems"] = [{"goal_id": 0, "name": "dag", "line": 1, "rule": "goal", "hypotheses": [],
                    "hypothesis_origins": [], "conclusion": goal, "statement": "",
                    "goal_fingerprint": 0}]
refused(dag, "exponential-dag", "over-budget", "identity-budget")
