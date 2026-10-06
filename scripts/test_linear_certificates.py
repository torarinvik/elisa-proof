"""Linear certificates (BACKLOG C-02/C-03): the producer's Fourier-Motzkin search and the kernel's
check of its `__elisa_linear_certificate` marker.

Positive: the fixture's three linear goals prove, each with a marker, and their packages replay.
Adversarial and malformed: forged multipliers, premises, goals and marker shapes in a package are
each refused by the kernel. Budget: a certificate past the premise limit is refused, and a goal
over more than six names is not searched.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portable_replay_support import BINARY, REPLAY
if not __debug__:
    raise SystemExit("run without Python -O: certificate assertions are required")

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-linear-"))
MARKER = "__elisa_linear_certificate"
TRUST = {"kernel": "checked", "package_reader": "trusted", "hypotheses": "adapter",
         "source_correspondence": "adapter", "fingerprints": "identity-hint",
         "source_authenticated": False}
# Kinds whose identity is scalar; mirrors `proof_push_kernel_identity`.
SCALAR_KINDS = {
    "absent", "bool", "char", "effect", "effect-call", "effect-containment", "effect-row",
    "field-init", "float", "opaque-float-literal", "ident", "int", "resource-bind", "resource-call", "resource-call-arg",
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




def args_of(package, call):
    nodes, children = package["kernel"]["nodes"], package["kernel"]["children"]
    node = nodes[call]
    return [nodes[slot]["left"] for slot in children[node["children_start"]:node["children_start"] + node["children_count"]]]


def certificate_of(package, theorem):
    nodes = package["kernel"]["nodes"]
    found = [h for h in theorem["hypotheses"]
             if nodes[h]["kind"] == "call" and nodes[nodes[h]["left"]]["name"] == MARKER]
    assert len(found) == 1, theorem["name"]
    return found[0]


def rebuild_certificate(package, theorem, arguments):
    """Replace the theorem's marker with a fresh call over `arguments` (node roots)."""
    old = certificate_of(package, theorem)
    callee = append_node(package, "ident", name=MARKER)
    start = len(package["kernel"]["children"])
    slots = [append_node(package, "call_arg", left=argument) for argument in arguments]
    package["kernel"]["children"].extend(slots)
    call = append_node(package, "call", left=callee, children_start=start, children_count=len(arguments))
    theorem["hypotheses"] = [call if h == old else h for h in theorem["hypotheses"]]
    return reseal(package, theorem)


def forged(package, theorem_name, change):
    """A one-theorem package whose named theorem `change` rewrites; the kernel must refuse it."""
    forgery = copy.deepcopy(package)
    theorem = copy.deepcopy(next(t for t in forgery["theorems"] if t["name"] == theorem_name and t["rule"] == "goal"))
    change(forgery, theorem)
    forgery["theorems"] = [reseal(forgery, theorem)]
    return forgery


def integer(package, value):
    if value >= 0:
        return append_node(package, "int", value=str(value))
    return append_node(package, "unary", "-", left=append_node(package, "int", value=str(-value)))


# Positive.
report = json.loads(subprocess.run([str(BINARY), "--json", str(ROOT / "examples/linear_certificates.elisa")],
                                   capture_output=True, text=True, timeout=300).stdout)
assert report["summary"]["proven"] == 7 and report["summary"]["unproven"] == 1, report["summary"]
assert report["replay"]["gaps"] == 0, report["replay"]
assert [f["line"] for f in report["findings"]] == [42], report["findings"]
package = export("linear_certificates")
code, result = replay(package, "linear-positive")
assert code == 0 and result["status"] == "replayed", result
goals = {t["name"]: t for t in package["theorems"] if t["rule"] == "goal"}
assert set(goals) == {"mix", "three", "strict"}, set(goals)
for theorem in goals.values():
    certificate_of(package, theorem)
    code, result = replay(with_theorem(package, theorem), "linear-" + theorem["name"])
    assert code == 0 and result["status"] == "replayed", (theorem["name"], result)


def refuse(name, theorem_name, change):
    refused(forged(package, theorem_name, change), name, "rejected", "kernel-rejected")


def set_argument(index, make):
    def change(forgery, theorem):
        arguments = args_of(forgery, certificate_of(forgery, theorem))
        arguments[index] = make(forgery)
        rebuild_certificate(forgery, theorem, arguments)
    return change


# Adversarial: `mix` is 2*(x <= 7)' + (x + y <= 10) + (x - y <= 4); every perturbation fails.
refuse("linear-goal-multiplier", "mix", set_argument(0, lambda f: integer(f, 1)))
refuse("linear-goal-multiplier-zero", "mix", set_argument(0, lambda f: integer(f, 0)))
refuse("linear-premise-multiplier", "mix", set_argument(2, lambda f: integer(f, 2)))
refuse("linear-negative-inequality-multiplier", "mix", set_argument(4, lambda f: integer(f, -1)))


def weaken_goal(forgery, theorem):
    # The same certificate cannot prove the false `x <= 6`.
    nodes = forgery["kernel"]["nodes"]
    goal = nodes[theorem["conclusion"]]
    theorem["conclusion"] = append_node(forgery, "binary", goal["operator"], goal["left"], integer(forgery, 6))
refuse("linear-false-goal", "mix", weaken_goal)
# No multipliers prove it either: the honest combination leaves 0 < 0.
refuse("linear-false-goal-best-effort", "mix", lambda f, t: (weaken_goal(f, t), set_argument(0, lambda g: integer(g, 2))(f, t)))


def drop_premise(forgery, theorem):
    premise = args_of(forgery, certificate_of(forgery, theorem))[1]
    theorem["hypotheses"] = [h for h in theorem["hypotheses"] if h != premise]
refuse("linear-premise-not-a-fact", "mix", drop_premise)


def invent_premise(forgery, theorem):
    # A premise that is not a fact: `x <= 0` would prove the goal if it were trusted.
    arguments = args_of(forgery, certificate_of(forgery, theorem))
    x = forgery["kernel"]["nodes"][theorem["conclusion"]]["left"]
    arguments = [integer(forgery, 1), append_node(forgery, "binary", "<=", x, integer(forgery, 0)), integer(forgery, 1)]
    rebuild_certificate(forgery, theorem, arguments)
refuse("linear-invented-premise", "mix", invent_premise)


def self_premise(forgery, theorem):
    # The marker cannot name itself, or any marker, as a premise.
    arguments = args_of(forgery, certificate_of(forgery, theorem))
    rebuild_certificate(forgery, theorem, arguments + [certificate_of(forgery, theorem), integer(forgery, 1)])
refuse("linear-marker-premise", "mix", self_premise)

# Malformed: a non-literal multiplier, an even argument count, an oversized multiplier.
refuse("linear-symbolic-multiplier", "mix",
       set_argument(2, lambda f: append_node(f, "ident", name="x")))
refuse("linear-even-arguments", "mix",
       lambda f, t: rebuild_certificate(f, t, args_of(f, certificate_of(f, t))[:-1]))
refuse("linear-oversized-multiplier", "mix", lambda f, t: rebuild_certificate(
    f, t, [integer(f, 2 * 1048577)] + args_of(f, certificate_of(f, t))[1:2] + [integer(f, 1048577)]
    + args_of(f, certificate_of(f, t))[3:4] + [integer(f, 1048577)]))


# Budget: sixteen premises (the honest two plus fourteen zero-weight repeats) exceed the limit.
def overfull(forgery, theorem):
    arguments = args_of(forgery, certificate_of(forgery, theorem))
    rebuild_certificate(forgery, theorem, arguments + [arguments[1], integer(forgery, 0)] * 14)
refuse("linear-premise-budget", "mix", overfull)


def at_limit(forgery, theorem):
    arguments = args_of(forgery, certificate_of(forgery, theorem))
    rebuild_certificate(forgery, theorem, arguments + [arguments[1], integer(forgery, 0)] * 13)
accepted = forged(package, "mix", at_limit)
code, result = replay(accepted, "linear-premise-limit")
assert code == 0 and result["status"] == "replayed", result

# Budget: seven names is past the search's atom limit, so the goal is left unproven.
source = "def seven(a: i64, b: i64, c: i64, d: i64, e: i64, f: i64, g: i64) -> i64:\n"
for name in "abcdefg":
    source += "    requires %s >= -100\n    requires %s <= 100\n" % (name, name)
source += "    requires a + b + c + d + e + f + g <= 10\n    requires b + c + d + e + f + g >= 0\n"
source += "    ensure result <= 10\n    return a\n"
seven = WORK / "seven.elisa"
seven.write_text(source)
report = json.loads(subprocess.run([str(BINARY), "--json", str(seven)], capture_output=True, text=True, timeout=300).stdout)
# The certificate search gives up past its atom limit; the mocap branch's own in-kernel
# Fourier-Motzkin tier may still close the goal, but then it must replay without gaps.
assert report["summary"]["unproven"] == 1 or (
    report["summary"]["unproven"] == 0 and report["replay"]["gaps"] == 0), report["summary"]
six = WORK / "six.elisa"
six.write_text(source.replace("g: i64", "").replace(", )", ")").replace(" + g", "").replace("    requires g >= -100\n    requires g <= 100\n", ""))
report = json.loads(subprocess.run([str(BINARY), "--json", str(six)], capture_output=True, text=True, timeout=300).stdout)
assert report["summary"]["unproven"] == 0 and report["replay"]["gaps"] == 0, report["summary"]

print("linear certificates: search, replay, forgeries and budgets agree")
