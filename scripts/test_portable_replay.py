"""Portable replay packages: `--package` exports, `elisa-proof-replay` re-checks with the kernel.

The checker links no compiler front end, search engine or AI client, so these tests drive it
only through package files. Positive packages come from real examples; every forgery below is
made consistent (statement and fingerprint recomputed) so that the kernel, not a checksum, is
what refuses it.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile

if not __debug__:
    raise SystemExit("portable replay checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
REPLAY = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-portable-"))

# One example per kernel rule family, each small enough to keep the suite quick.
POSITIVE = {
    "global_constant_module": {"goal", "resource-safety"},
    "module_negative_i64_constant_contract": {"goal", "resource-safety"},
    "verified": {"goal"},
    "collection_quantifier": {"quantifier-forall", "quantifier-exists"},
    "checked_index_fallback": {"checked-index"},
    "getelse_recovery": {"checked-get"},
    "effect_containment": {"effect-containment"},
    "implicit_structural_decreases": {"structural-safety"},
    "early_return_index_guard": {"index-lower", "index-upper"},
    "fixed_array_slice_bounds": {"slice-lower", "slice-upper", "slice-order"},
    "pure_unfolding": {"goal"},
    "goal_disjunct_split_probe": {"goal", "resource-safety"},
    "disjunctive_goals": {"goal", "index-upper"},
    "leaving_branch_join": {"goal", "index-upper"},
}
TRUST = {"kernel": "checked", "package_reader": "trusted", "hypotheses": "adapter",
         "source_correspondence": "adapter", "fingerprints": "identity-hint",
         "source_authenticated": False}
# Kinds whose identity is scalar: atoms, and certificate roots whose structure the dedicated
# kernel replays. Mirrors `proof_push_kernel_identity`.
SCALAR_KINDS = {
    "absent", "bool", "char", "effect", "effect-call", "effect-containment", "effect-row",
    "field-init", "float", "ident", "int", "resource-bind", "resource-call", "resource-call-arg",
    "resource-call-formal", "resource-call-lend", "resource-call-region", "resource-call-result",
    "resource-disjoint", "resource-join-move", "resource-move", "resource-region-alloc",
    "resource-region-alloc-discard", "resource-region-assign", "resource-region-bind",
    "resource-region-call-alloc", "resource-region-close", "resource-region-open",
    "resource-region-param", "resource-region-rebind-alloc", "resource-region-return",
    "resource-region-return-alloc", "resource-safety", "resource-scope", "resource-use",
    "resource-write", "resource-write-readonly", "shorthand", "string", "structural-argument",
    "structural-edge", "structural-safety", "unsupported",
}
LEFT = {"unary", "move", "field", "scope", "call_arg", "checked-get"}
LEFT_RIGHT = {"binary", "index", "checked-index", "dict_entry"}
THREE = {"if", "slice"}
HEAD_CHILDREN = {"call", "index-n", "construct", "record-update"}
CHILDREN = {"array", "tuple", "set", "dict"}


def json_string(text):
    out = ['"']
    for char in text:
        code = ord(char)
        if char in '"\\':
            out.append("\\" + char)
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif code < 32:
            out.append("\\u%04x" % code)
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def identity(nodes, children, root, depth=0):
    assert depth < 128 and root < len(nodes)
    node = nodes[root]
    kind = node["kind"]
    text = "(%s:%s:%s:%s:%s" % (kind, node["operator"], node["value"],
                                json_string(node["name"]), json_string(node["secondary_name"]))
    parts = []
    if kind in LEFT:
        parts = [node["left"]]
    elif kind in LEFT_RIGHT:
        parts = [node["left"], node["right"]]
    elif kind in THREE:
        parts = [node["left"], node["right"], node["auxiliary"]]
    elif kind in HEAD_CHILDREN or kind in CHILDREN:
        start, count = node["children_start"], node["children_count"]
        parts = ([node["left"]] if kind in HEAD_CHILDREN else []) + children[start:start + count]
    elif kind == "quantifier":
        text += ":%d" % node["auxiliary"]
        parts = [node["left"], node["right"]]
    else:
        assert kind in SCALAR_KINDS, kind
    return text + "".join(identity(nodes, children, part, depth + 1) for part in parts) + ")"


def statement(package, hypotheses, conclusion):
    nodes, children = package["kernel"]["nodes"], package["kernel"]["children"]
    return ("elisa-proof-goal-v1:" + "".join("F" + identity(nodes, children, h) for h in hypotheses)
            + "G" + identity(nodes, children, conclusion))


def fnv1a32(text):
    value = 2166136261
    for byte in text.encode("utf-8"):
        value = ((value ^ byte) * 16777619) % 2**32
    return value


def reseal(package, theorem):
    """Recompute a theorem's statement and fingerprint after a forgery."""
    theorem["statement"] = statement(package, theorem["hypotheses"], theorem["conclusion"])
    theorem["goal_fingerprint"] = fnv1a32(theorem["statement"])
    theorem["hypothesis_origins"] = theorem["hypothesis_origins"][:len(theorem["hypotheses"])]
    while len(theorem["hypothesis_origins"]) < len(theorem["hypotheses"]):
        theorem["hypothesis_origins"].append({"kind": "forged"})
    return theorem


def export(example):
    run = subprocess.run([str(BINARY), "--package", str(ROOT / "examples" / (example + ".elisa"))],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode in (0, 1), (example, run.returncode, run.stderr)
    return json.loads(run.stdout)


def replay_text(text, name):
    path = WORK / (name + ".json")
    path.write_text(text)
    run = subprocess.run([str(REPLAY), str(path)], capture_output=True, text=True, timeout=120)
    result = json.loads(run.stdout)
    assert result["format"] == "elisa-proof-replay-result-v1", result
    if run.returncode == 2:
        return run.returncode, result
    assert result["trust"] == TRUST, result
    expected_exit = 0 if result["status"] == "replayed" else 1
    assert run.returncode == expected_exit, (name, run.returncode, result["status"])
    return run.returncode, result


def replay(package, name):
    return replay_text(json.dumps(package), name)


def refused(package_or_text, name, status, reason):
    if isinstance(package_or_text, str):
        code, result = replay_text(package_or_text, name)
    else:
        code, result = replay(package_or_text, name)
    assert code == 1 and result["status"] == status and result["reason"] == reason, (name, result)
    return result


def with_theorem(package, theorem):
    forged = copy.deepcopy(package)
    forged["theorems"] = [copy.deepcopy(theorem)]
    return forged


def append_node(package, kind, operator="", left=0, right=0, value="0", name="",
                children_start=0, children_count=0, auxiliary=0, secondary_name=""):
    nodes = package["kernel"]["nodes"]
    nodes.append({"kind": kind, "operator": operator, "left": left, "right": right,
                  "auxiliary": auxiliary, "children_start": children_start, "children_count": children_count,
                  "value": value, "name": name, "secondary_name": secondary_name})
    return len(nodes) - 1


# Positive: every exported theorem replays, and the Python encoder agrees with the exporter.
packages = {}
for example, rules in POSITIVE.items():
    package = export(example)
    packages[example] = package
    assert package["format"] == "elisa-proof-package-v1" and package["source"]["admissible"], example
    assert package["source"]["authenticated"] is False, example
    seen = {theorem["rule"] for theorem in package["theorems"]}
    assert rules <= seen, (example, rules, seen)
    for theorem in package["theorems"]:
        assert theorem["statement"] == statement(package, theorem["hypotheses"], theorem["conclusion"]), (example, theorem["name"])
        assert theorem["goal_fingerprint"] == fnv1a32(theorem["statement"]), (example, theorem["name"])
    code, result = replay(package, example)
    assert code == 0 and result["status"] == "replayed", (example, result)
    assert result["summary"] == {"theorems": len(package["theorems"]),
                                 "replayed": len(package["theorems"]), "not_replayed": 0}, result
    report = json.loads(subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (example + ".elisa"))],
                                       capture_output=True, text=True, timeout=120).stdout)
    replayed_goals = [goal for goal in report["goals"] if goal["proven"] and goal.get("replay_status") == "replayed"]
    assert len(package["theorems"]) == len(replayed_goals), (example, len(package["theorems"]), len(replayed_goals))

# Replay scratch (quantifier binder markers) is not exported: the arena ends at the last root.
quantified = packages["collection_quantifier"]
last_root = max(max([t["conclusion"]] + t["hypotheses"]) for t in quantified["theorems"])
assert len(quantified["kernel"]["nodes"]) == last_root + 1, (len(quantified["kernel"]["nodes"]), last_root)
assert not any(node["name"].startswith("__elisa_kernel_quantifier") for node in quantified["kernel"]["nodes"])

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

base = packages["verified"]
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

# Header, trust and schema: nothing is inferred, over-claimed or accepted twice.
text = json.dumps(with_theorem(base, assumption))
refused(text.replace('{"format": ', '{"format": "elisa-proof-package-v1", "format": ', 1),
        "duplicate-key", "malformed", "package-schema")
extra = with_theorem(base, assumption)
extra["kernel"]["nodes"][0]["proof"] = True
refused(extra, "extra-node-key", "malformed", "node-schema")
extra = with_theorem(base, assumption)
extra["theorems"][0]["trusted"] = True
refused(extra, "extra-theorem-key", "malformed", "theorem-schema")
for key, value in (("hypotheses", "kernel"), ("source_correspondence", "checked"), ("fingerprints", "digest")):
    claim = with_theorem(base, assumption)
    claim["trust"][key] = value
    refused(claim, "trust-" + key, "malformed", "trust-schema")
claim = with_theorem(base, assumption)
claim["source"]["authenticated"] = True
refused(claim, "authenticated", "malformed", "source-schema")
claim = with_theorem(base, assumption)
claim["source"]["admissible"] = False
refused(claim, "inadmissible", "rejected", "source-inadmissible")
claim = with_theorem(base, assumption)
claim["format"] = "elisa-proof-package-v2"
refused(claim, "format", "malformed", "format")
for bad in ("01", "-0", "+1", "", " 1", "9223372036854775808", "-9223372036854775809", "1e3"):
    claim = with_theorem(base, assumption)
    claim["kernel"]["nodes"][0]["value"] = bad
    refused(claim, "value-" + bad, "malformed", "node-schema")
claim = with_theorem(base, assumption)
claim["kernel"]["nodes"][0]["value"] = 0
refused(claim, "value-number", "malformed", "node-schema")
for bad in (1.5, -1, 2**53, "3", True):
    claim = with_theorem(base, assumption)
    claim["theorems"][0]["conclusion"] = bad
    refused(claim, "index-%r" % (bad,), "malformed", "theorem-schema")
claim = with_theorem(base, assumption)
claim["theorems"][0]["hypothesis_origins"] = []
refused(claim, "origins", "malformed", "theorem-schema")
refused(with_theorem(base, assumption) | {"theorems": []}, "empty", "rejected", "no-theorems")
refused(text[:-2], "truncated", "malformed", "json")
refused("", "empty-file", "malformed", "json")

# Extreme i64 values round-trip exactly as decimal strings.
extreme = copy.deepcopy(base)
low = append_node(extreme, "int", value="-9223372036854775808")
high = append_node(extreme, "int", value="9223372036854775807")
claim = copy.deepcopy(assumption)
claim["conclusion"] = append_node(extreme, "binary", "<", low, high)
extreme["theorems"] = [reseal(extreme, claim)]
assert "(int::-9223372036854775808:" in extreme["theorems"][0]["statement"]
# The kernel may decline to compare width-ambiguous constants; the reader must still read them
# exactly, so the recomputed statement matches, and a value one off does not.
code, result = replay(extreme, "extreme-values")
assert result["reason"] in (None, "kernel-rejected"), result
extreme["kernel"]["nodes"][high]["value"] = "9223372036854775806"
refused(extreme, "extreme-value-off-by-one", "rejected", "statement-mismatch")

# Budgets are checked before the work they bound.
huge = with_theorem(base, assumption)
huge["kernel"]["nodes"] = [{}] * 1000001
refused(huge, "node-budget", "over-budget", "node-budget")
huge = with_theorem(base, assumption)
huge["kernel"]["children"] = [0] * 4000001
refused(huge, "child-budget", "over-budget", "child-budget")
many = copy.deepcopy(assumption)
many["hypotheses"] = [0] * 4097
many["hypothesis_origins"] = [{}] * 4097
refused(with_theorem(base, many), "hypothesis-budget", "over-budget", "hypothesis-budget")
flood = with_theorem(base, assumption)
flood["theorems"] = [{}] * 65537
refused(flood, "theorem-budget", "over-budget", "theorem-budget")

# One bad theorem among good ones fails the package and is named; the rest still replay.
mixed = copy.deepcopy(packages["global_constant_module"])
bad = copy.deepcopy(mixed["theorems"][0])
bad["goal_fingerprint"] = (bad["goal_fingerprint"] + 1) % 2**32
mixed["theorems"].insert(1, bad)
result = refused(mixed, "mixed", "rejected", "fingerprint-mismatch")
assert result["summary"] == {"theorems": len(mixed["theorems"]), "replayed": len(mixed["theorems"]) - 1,
                             "not_replayed": 1}, result
assert [t["status"] for t in result["theorems"]].count("rejected") == 1, result

# Usage and unreadable input exit 2.
usage = subprocess.run([str(REPLAY)], capture_output=True, text=True, timeout=30)
assert usage.returncode == 2 and "usage" in usage.stdout, usage
missing = subprocess.run([str(REPLAY), str(WORK / "missing.json")], capture_output=True, text=True, timeout=30)
assert missing.returncode == 2 and json.loads(missing.stdout)["status"] == "unreadable", missing

print("portable replay: %d packages replay; forgeries, forged arenas, schema, trust and budgets are refused"
      % len(packages))
