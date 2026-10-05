"""Adversarial resource traces shared by the portable replay matrix."""
import copy
import json
import subprocess


def check_reader_usage(replay_binary, work):
    usage = subprocess.run([str(replay_binary)], capture_output=True, text=True, timeout=30)
    if usage.returncode != 2 or "usage" not in usage.stdout:
        raise AssertionError(usage)
    missing = subprocess.run([str(replay_binary), str(work / "missing.json")],
                             capture_output=True, text=True, timeout=30)
    if missing.returncode != 2 or json.loads(missing.stdout)["status"] != "unreadable":
        raise AssertionError(missing)


def check_unresolved_shadow(packages, refused):
    # Qualifying declared constants must not grant arbitrary local names static storage.
    shadow_trace = copy.deepcopy(packages["replay_qualified_constant_argument"])
    nodes = shadow_trace["kernel"]["nodes"]
    children = shadow_trace["kernel"]["children"]
    shadow_leaf = None
    for lend in nodes:
        if lend["kind"] not in ("resource-call", "resource-call-lend") or lend["name"] != "accept_signed":
            continue
        for arg_id in children[lend["children_start"]:lend["children_start"] + lend["auxiliary"]]:
            arg = nodes[arg_id]
            if arg["kind"] != "resource-call-arg" or arg["name"] != "value":
                continue
            expression = arg["left"]
            if expression >= len(nodes) or nodes[expression]["kind"] != "unary":
                continue
            arithmetic = nodes[expression]["left"]
            if arithmetic >= len(nodes) or nodes[arithmetic]["kind"] != "binary":
                continue
            leaf = nodes[arithmetic]["left"]
            if leaf < len(nodes) and nodes[leaf]["kind"] == "ident" and nodes[leaf]["name"] == "SIGNED_DEPTH":
                shadow_leaf = leaf
    if shadow_leaf is None:
        raise AssertionError("shadowed constant trace was not found")
    nodes[shadow_leaf]["name"] = "UNRESOLVED_SHADOW_VALUE"
    refused(shadow_trace, "unresolved-shadowed-resource-value", "rejected", "kernel-rejected")
