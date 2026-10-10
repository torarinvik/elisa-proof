"""Shared builders and identity/replay helpers for portable replay tests."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

__all__ = (
    "BINARY", "CHILDREN", "HEAD_CHILDREN", "LEFT", "LEFT_RIGHT", "REPLAY", "ROOT",
    "SCALAR_KINDS", "THREE", "TRUST", "WORK", "append_node", "export", "fnv1a32",
    "identity", "json_string", "refused", "replay", "replay_text", "reseal", "statement",
    "with_theorem",
)

if not __debug__:
    raise SystemExit("portable replay checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]


def resolve_products():
    """Select one published product generation, or honor an explicit paired override."""
    proof_override = os.environ.get("ELISA_PROOF_BIN")
    replay_override = os.environ.get("ELISA_PROOF_REPLAY_BIN")
    if proof_override or replay_override:
        if not proof_override or not replay_override:
            raise RuntimeError("portable replay requires both ELISA_PROOF_BIN and ELISA_PROOF_REPLAY_BIN")
        return Path(proof_override), Path(replay_override)

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_product_pair.py"), "resolve",
         "--generation-root", os.environ.get("ELISA_PROOF_GENERATION_ROOT",
                                               str(ROOT / "build/elisa-proof-generations"))],
        capture_output=True, text=True, check=True,
    )
    products = json.loads(result.stdout)["products"]
    return (Path(products["elisa-proof"]["binary"]),
            Path(products["elisa-proof-replay"]["binary"]))


BINARY, REPLAY = resolve_products()
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-portable-"))

TRUST = {"kernel": "checked", "package_reader": "trusted", "hypotheses": "adapter",
         "source_correspondence": "adapter", "fingerprints": "identity-hint",
         "source_authenticated": False}
SCALAR_KINDS = {
    "frame-field", "absent", "bool", "char", "effect", "effect-call", "effect-containment", "effect-row",
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
    elif kind in ("frame-place", "frame-policy"):
        text += ":%d" % node["auxiliary"]
        if kind == "frame-policy":
            text += ":%d" % node["right"]
        start, count = node["children_start"], node["children_count"]
        parts = ([node["left"]] if kind == "frame-policy" else []) + children[start:start + count]
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
    path.write_bytes(text) if isinstance(text, bytes) else path.write_text(text)
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
    if isinstance(package_or_text, (str, bytes)):
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
