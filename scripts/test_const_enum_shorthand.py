#!/usr/bin/env python3
"""Owner-aware const-enum shorthand proof and independent portable replay gates."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
REPLAY = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay"))
if not __debug__:
    raise SystemExit("test_const_enum_shorthand.py must run without Python -O")

POSITIVE = {
    "expression_witness": "const_enum_reflexive",
    "shorthand_member": "shorthand_member_value",
}
NEGATIVE = {
    "rejected_ambiguous_const_enum_shorthand": "ambiguous_samevariantacrossowners",
    "rejected_payload_enum_shorthand": "payload_enum_shorthand",
    "rejected_wrong_enum_shorthand_variant": "wrongvariant",
    "rejected_overloaded_const_enum_equality": "sourceoverloadedEq",
    "rejected_module_crossscope_const_enum_shorthand": "module_crossscope_ambiguous",
}
SOURCE_FALSE_CLAIMS = {
    "unique-variant-values": ("""const enum AuditOption of i64:
    None = 0
    Some = 1

def source_false_unique_variant(option: AuditOption) -> bool:
    requires option == .None
    ensure result == true
    return option == .Some
""", "source_false_unique_variant", "Some", True),
    "cross-owner-variant-collision": ("""const enum AuditOption of i64:
    None = 0
    Some = 1

const enum AuditOtherOption of i64:
    None = 7

def source_false_owner_collision(option: AuditOption) -> bool:
    requires option == .None
    ensure result == true
    return option == .Some
""", "source_false_owner_collision", "Some", True),
    "payload-enum-type-collision": ("""const enum AuditOption of i64:
    None = 0
    Some = 1

enum AuditPayloadOption:
    None

def source_false_payload_collision(option: AuditOption) -> bool:
    requires option == .None
    ensure result == true
    return option == .Some
""", "source_false_payload_collision", "Some", True),
    "foreign-owner-wrong-type-proof-refusal": ("""const enum AuditOption of i64:
    None = 0
    Some = 1

const enum AuditForeignOption of i64:
    Foreign = 9

def source_false_foreign_variant(option: AuditOption) -> bool:
    requires option == .None
    ensure result == true
    return option == .Foreign
""", "source_false_foreign_variant", "Foreign", False),
}

# Keep this portable identity encoder aligned with test_portable_replay.py. Forgery
# tests reseal the statement and fingerprint so replay, not package integrity, decides.
SCALAR_KINDS = {
    "absent", "bool", "char", "effect", "effect-call", "effect-containment", "effect-row",
    "field-init", "float", "ident", "int", "resource-bind", "resource-call",
    "resource-call-arg", "resource-call-formal", "resource-call-lend", "resource-call-region",
    "resource-call-result", "resource-disjoint", "resource-join-move", "resource-move",
    "resource-region-alloc", "resource-region-alloc-discard", "resource-region-assign",
    "resource-region-bind", "resource-region-call-alloc", "resource-region-close",
    "resource-region-open", "resource-region-param", "resource-region-rebind-alloc",
    "resource-region-return", "resource-region-return-alloc", "resource-safety", "resource-scope",
    "resource-use", "resource-write", "resource-write-readonly", "shorthand", "string",
    "structural-argument", "structural-edge", "structural-safety", "unsupported",
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
        parts = []
    return text + "".join(identity(nodes, children, part, depth + 1) for part in parts) + ")"


def reseal(package, theorem):
    nodes, children = package["kernel"]["nodes"], package["kernel"]["children"]
    theorem["statement"] = ("elisa-proof-goal-v1:" +
                            "".join("F" + identity(nodes, children, h) for h in theorem["hypotheses"]) +
                            "G" + identity(nodes, children, theorem["conclusion"]))
    fingerprint = 2166136261
    for byte in theorem["statement"].encode("utf-8"):
        fingerprint = ((fingerprint ^ byte) * 16777619) % 2**32
    theorem["goal_fingerprint"] = fingerprint
    theorem["hypothesis_origins"] = theorem["hypothesis_origins"][:len(theorem["hypotheses"])]
    while len(theorem["hypothesis_origins"]) < len(theorem["hypotheses"]):
        theorem["hypothesis_origins"].append({"kind": "forged"})
    return theorem


def isolated_claim(package, theorem):
    result = copy.deepcopy(package)
    result["theorems"] = [copy.deepcopy(theorem)]
    return result


def scalar_shorthand_marker(package, theorem, member):
    nodes = package["kernel"]["nodes"]
    children = package["kernel"]["children"]
    found = []
    for hypothesis in theorem["hypotheses"]:
        call = nodes[hypothesis]
        if call["kind"] != "call" or nodes[call["left"]]["name"] != "__elisa_primitive_scalar_type":
            continue
        arguments = [children[index] for index in
                     range(call["children_start"], call["children_start"] + call["children_count"])]
        if len(arguments) != 1 or nodes[arguments[0]]["kind"] != "call_arg":
            continue
        term = nodes[arguments[0]]["left"]
        if nodes[term]["kind"] == "shorthand" and nodes[term]["name"] == member:
            found.append((hypothesis, term))
    assert len(found) == 1, (theorem["name"], member, found)
    return found[0]


def transplant_scalar_marker(donor, marker, recipient):
    """Copy a one-argument shorthand scalar marker into another package's graph."""
    source_nodes = donor["kernel"]["nodes"]
    source_children = donor["kernel"]["children"]
    call = source_nodes[marker]
    assert call["kind"] == "call" and call["children_count"] == 1
    callee = source_nodes[call["left"]]
    assert callee["kind"] == "ident" and callee["name"] == "__elisa_primitive_scalar_type"
    wrapper_index = source_children[call["children_start"]]
    wrapper = source_nodes[wrapper_index]
    assert wrapper["kind"] == "call_arg"
    term = source_nodes[wrapper["left"]]
    assert term["kind"] == "shorthand"

    target_nodes = recipient["kernel"]["nodes"]
    target_children = recipient["kernel"]["children"]
    new_callee = len(target_nodes)
    target_nodes.append(copy.deepcopy(callee))
    new_term = len(target_nodes)
    target_nodes.append(copy.deepcopy(term))
    new_wrapper = len(target_nodes)
    target_nodes.append(dict(wrapper, left=new_term))
    child_start = len(target_children)
    target_children.append(new_wrapper)
    new_call = len(target_nodes)
    target_nodes.append(dict(call, left=new_callee, children_start=child_start, children_count=1))
    return new_call


def run_json(command):
    completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
    try:
        value = json.loads(completed.stdout)
    except Exception as exc:
        raise AssertionError((command, completed.returncode, completed.stderr[-2000:])) from exc
    assert completed.returncode in (0, 1), (command, completed.returncode, completed.stderr[-2000:])
    return completed, value


def package_replay(package, directory, stem):
    path = directory / (stem + ".json")
    path.write_text(json.dumps(package))
    completed, result = run_json([str(REPLAY), str(path)])
    assert completed.returncode == 0 and result["status"] == "replayed", (stem, result)
    assert result["summary"]["replayed"] == result["summary"]["theorems"], (stem, result)


with tempfile.TemporaryDirectory(prefix="elisa-enum-shorthand-") as temporary:
    scratch = Path(temporary)
    positive_packages = {}
    for example, target in POSITIVE.items():
        source = ROOT / "examples" / (example + ".elisa")
        completed, report = run_json([str(PROOF), "--json", str(source)])
        assert report["status"] == "proved", (example, report["summary"], report["findings"])
        assert report["replay"]["gaps"] == 0
        assert report["replay"]["certificates"] == report["replay"]["replayed"]
        assert any(goal["name"] == target and goal["proven"] and goal["replay_status"] == "replayed"
                   for goal in report["goals"]), (example, target)
        package_run, package = run_json([str(PROOF), "--package", str(source)])
        assert package["source"]["admissible"]
        assert any(theorem["name"] == target for theorem in package["theorems"]), (example, target)
        package_replay(package, scratch, example)
        positive_packages[example] = package
        print("positive:", example, "producer and portable replay passed")

    # Isolate the owner-bound claims as portable positive controls. Later paired
    # marker mutations preserve the claim and report replay's actual verdict without
    # assuming that the portable kernel authenticates source typing metadata.
    expression_package = positive_packages["expression_witness"]
    expression_claim = next(theorem for theorem in expression_package["theorems"]
                            if theorem["name"] == POSITIVE["expression_witness"] and theorem["rule"] == "goal")
    shorthand_package = positive_packages["shorthand_member"]
    shorthand_claim = next(theorem for theorem in shorthand_package["theorems"]
                           if theorem["name"] == POSITIVE["shorthand_member"] and theorem["rule"] == "goal")
    package_replay(isolated_claim(expression_package, expression_claim), scratch,
                   "expression-witness-portable-control")
    package_replay(isolated_claim(shorthand_package, shorthand_claim), scratch,
                   "shorthand-member-portable-control")

    # Producer-backed marker-sensitivity control: option == .None entails
    # .None == option. Genuine portable replay must accept this exact nontrivial
    # conclusion before either mutation is attempted.
    symmetry_source = scratch / "marker-sensitivity.elisa"
    symmetry_source.write_text("""const enum MarkerSensitivityOption of i64:
    None = 0
    Some = 1

def marker_sensitivity_symmetry(option: MarkerSensitivityOption) -> bool:
    requires option == .None
    ensure .None == option
    return true
""")
    _, symmetry_report = run_json([str(PROOF), "--json", str(symmetry_source)])
    assert symmetry_report["status"] == "proved" and symmetry_report["replay"]["gaps"] == 0
    _, symmetry_package = run_json([str(PROOF), "--package", str(symmetry_source)])
    symmetry_claim = next(theorem for theorem in symmetry_package["theorems"]
                          if theorem["name"] == "marker_sensitivity_symmetry" and theorem["rule"] == "goal")
    genuine = isolated_claim(symmetry_package, symmetry_claim)
    package_replay(genuine, scratch, "genuine-marker-sensitivity-control")

    # Keep the exact same theorem conclusion and every non-marker fact. Change only
    # the marker's shorthand variant, reseal identities, and ask portable replay.
    recipient_marker, marker_term = scalar_shorthand_marker(
        symmetry_package, symmetry_claim, "None")
    marker_only = isolated_claim(symmetry_package, symmetry_claim)
    marker_only["kernel"]["nodes"][marker_term]["name"] = "NotADeclaredVariant"
    marker_only_claim = marker_only["theorems"][0]
    assert marker_only_claim["conclusion"] == symmetry_claim["conclusion"]
    reseal(marker_only, marker_only_claim)
    marker_only_path = scratch / "marker-only-edit.json"
    marker_only_path.write_text(json.dumps(marker_only))
    edit_run, edit_result = run_json([str(REPLAY), str(marker_only_path)])

    # Transplant the valid .On marker fact from the expression_witness owner into
    # the symmetry theorem, replacing only its .None marker. Leave the proposition
    # byte-for-byte represented by the same conclusion node.
    donor_marker, _ = scalar_shorthand_marker(expression_package, expression_claim, "On")
    transplanted = isolated_claim(symmetry_package, symmetry_claim)
    transplanted_claim = transplanted["theorems"][0]
    transplanted_marker = transplant_scalar_marker(expression_package, donor_marker, transplanted)
    transplanted_claim["hypotheses"] = [
        transplanted_marker if hypothesis == recipient_marker else hypothesis
        for hypothesis in transplanted_claim["hypotheses"]
    ]
    assert transplanted_claim["conclusion"] == symmetry_claim["conclusion"]
    reseal(transplanted, transplanted_claim)
    transplanted_path = scratch / "cross-owner-enum-marker-transplant.json"
    transplanted_path.write_text(json.dumps(transplanted))
    transplant_run, transplant_result = run_json([str(REPLAY), str(transplanted_path)])
    for label, replay_run, replay_result in (
            ("marker edit", edit_run, edit_result),
            ("cross-owner transplant", transplant_run, transplant_result)):
        assert replay_run.returncode in (0, 1)
        assert replay_result["status"] in ("replayed", "rejected"), (label, replay_result)
        if replay_result["status"] == "rejected":
            assert replay_result["reason"] == "kernel-rejected", (label, replay_result)
    print("portable marker controls: genuine same-conclusion claim replayed;")
    print("  marker-only edit:", edit_result["status"],
          "cross-owner transplant:", transplant_result["status"])
    if edit_result["status"] == "replayed" or transplant_result["status"] == "replayed":
        print("  portable kernel did not establish sensitivity to every marker mutation;")
        print("  do not claim marker validation from these controls")

    # Source-bound attacks use the compiler-imported declarations and exact source goal,
    # unlike portable packages whose hypothesis provenance is adapter-authenticated. Each
    # source deliberately makes a false guarantee; its false target must remain open and be
    # omitted from --package. A source-bound `have` then tries the corresponding false fact
    # under the source precondition. The kernel must replay the rejection of that step.
    for case, (source_text, target, proposed_variant, require_semantic_clean) in SOURCE_FALSE_CLAIMS.items():
        source = scratch / ("source-audit-" + case + ".elisa")
        source.write_text(source_text)
        _, report = run_json([str(PROOF), "--json", str(source)])
        target_goals = [goal for goal in report["goals"]
                        if goal["name"] == target and goal["rule"] == "goal"]
        assert len(target_goals) == 1 and not target_goals[0]["proven"], (case, target_goals)
        assert report["status"] == "failed" and report["replay"]["gaps"] == 0
        assert report["replay"]["certificates"] == report["replay"]["replayed"]
        semantic_errors = report["summary"]["semantic_errors"]
        semantic_diagnostics = report["summary"]["semantic_diagnostics"]
        if require_semantic_clean:
            assert semantic_errors == 0 and semantic_diagnostics == 0, (case, report["summary"])
            assert report["semantic_diagnostics"] == [], (case, report["semantic_diagnostics"])
        else:
            assert any(finding.get("kind") == "expression-unsupported"
                       and finding.get("status") == "unsupported"
                       for finding in report["findings"]), (case, report["findings"])
        print("source diagnostics:", case,
              "semantic_errors=", semantic_errors,
              "semantic_diagnostics=", semantic_diagnostics,
              "details=", report["semantic_diagnostics"],
              "findings=", report["findings"] if not require_semantic_clean else [])

        _, package = run_json([str(PROOF), "--package", str(source)])
        assert package["source"]["admissible"] is True
        assert package["source"]["authenticated"] is False
        assert not any(theorem["name"] == target and theorem["rule"] == "goal"
                       for theorem in package["theorems"]), (case, target, package["theorems"])
        package_replay(package, scratch, "source-audit-package-" + case)

        # This is source-bound: the runner reloads source facts/goal, and the script cannot
        # replace them. `accepted:false` asks for the negative outcome to be replayed, not
        # admitted as a proof.
        script = scratch / ("source-audit-tactic-" + case + ".json")
        script.write_text(json.dumps({
            "format": "elisa-proof-tactics-v1",
            "target": {"goal_id": target_goals[0]["goal_id"]},
            "actions": [{
                "action": "have",
                "argument": {
                    "kind": "binary", "operator": "==",
                    "left": {"kind": "ident", "name": "option"},
                    "right": {"kind": "shorthand_member", "parts": [proposed_variant]},
                },
                "accepted": False,
            }],
        }))
        tactic_run, tactic = run_json([str(PROOF), "--tactics", str(script), str(source)])
        assert tactic_run.returncode == 1 and tactic["status"] == "failed"
        assert tactic["source"]["admissible"] is True and tactic["source"]["fingerprint_match"] is True
        assert tactic["source_goal_binding"]["bound"] is True
        assert tactic["source_goal_binding"]["goal_id"] == target_goals[0]["goal_id"]
        assert tactic["tactic"]["valid"] is True and tactic["tactic"]["solved"] is False
        assert tactic["tactic"]["trace_replayed"] is True
        assert tactic["tactic"]["kernel_trace_replayed"] is True
        assert tactic["tactic"]["certificate_replayed"] is False
        assert len(tactic["state"]["trace"]) == 1
        rejected_step = tactic["state"]["trace"][0]
        assert rejected_step["action"] == "have" and rejected_step["accepted"] is False
        assert rejected_step["reason"] == "the proposed fact is not entailed by the current hypotheses"
        classification = "valid source, 0 semantic errors/diagnostics" if require_semantic_clean else "foreign-owner wrong-type proof refusal"
        print("source audit:", case, classification,
              "false goal stayed unproven/unexported; source-bound false step refused and kernel-trace-replayed")

    # Matched satisfiable control: preserve the unique-enum source and its `None`
    # precondition/body, make the return false consistent with the false `Some` test,
    # and state the enum fact needed by the current proof fragment. This distinguishes
    # false-goal refusal from parser/type refusal without asserting a stronger enum rule.
    satisfiable_source = scratch / "source-audit-unique-variant-satisfiable.elisa"
    satisfiable_source.write_text("""const enum AuditOption of i64:
    None = 0
    Some = 1

def source_false_unique_variant(option: AuditOption) -> bool:
    requires option == .None and option != .Some
    ensure result == false
    return option == .Some
""")
    _, satisfiable_report = run_json([str(PROOF), "--json", str(satisfiable_source)])
    assert satisfiable_report["status"] == "proved", (satisfiable_report["summary"], satisfiable_report["findings"])
    assert satisfiable_report["summary"]["semantic_errors"] == 0
    assert satisfiable_report["summary"]["semantic_diagnostics"] == 0
    assert satisfiable_report["semantic_diagnostics"] == []
    assert satisfiable_report["replay"]["gaps"] == 0
    assert satisfiable_report["replay"]["certificates"] == satisfiable_report["replay"]["replayed"]
    assert any(goal["name"] == "source_false_unique_variant" and goal["rule"] == "goal"
               and goal["proven"] and goal["replay_status"] == "replayed"
               for goal in satisfiable_report["goals"])
    _, satisfiable_package = run_json([str(PROOF), "--package", str(satisfiable_source)])
    assert satisfiable_package["source"]["admissible"] is True
    assert any(theorem["name"] == "source_false_unique_variant" and theorem["rule"] == "goal"
               for theorem in satisfiable_package["theorems"])
    package_replay(satisfiable_package, scratch, "source-audit-unique-variant-satisfiable")
    print("source audit: matched unique-variant satisfiable control proved and fully replayed")

    for example, target in NEGATIVE.items():
        source = ROOT / "examples" / (example + ".elisa")
        _, report = run_json([str(PROOF), "--json", str(source)])
        assert report["replay"]["gaps"] == 0
        assert report["replay"]["certificates"] == report["replay"]["replayed"]
        target_goals = [goal for goal in report["goals"]
                        if goal["name"] == target and goal["rule"] != "resource-safety"]
        target_findings = [finding for finding in report["findings"] if finding.get("name") == target]
        assert (target_goals or target_findings) and not any(goal["proven"] for goal in target_goals), \
            (example, target, report["goals"], report["findings"])
        assert target_findings, (example, target, report["findings"])
        _, package = run_json([str(PROOF), "--package", str(source)])
        assert not any(theorem["name"] == target and theorem["rule"] != "resource-safety"
                       for theorem in package.get("theorems", [])), (example, target)
        if package["source"]["admissible"]:
            package_replay(package, scratch, example)
        print("negative:", example, "claim refused and absent from portable package")
