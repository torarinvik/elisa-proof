#!/usr/bin/env python3
"""Check the report's measurement section and the shape of the shared kernel arena."""
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent
KEYS = (
    "declarations", "obligations", "goal_attempts", "certificates", "certificate_facts",
    "largest_certificate_facts", "repeated_certificate_fact_roots", "fact_traces",
    "control_flow_steps", "live_facts_peak", "kernel_nodes", "kernel_nodes_shared",
    "kernel_children", "report_bytes",
)
# Kinds whose left/right/auxiliary fields are node references, in that order. Mirrors
# proof_kernel_intern_reference_fields; any kind missing here is not checked for ordering.
REFERENCE_FIELDS = {
    "unary": 1, "move": 1, "call_arg": 1, "field": 1, "scope": 1, "checked-get": 1,
    "field-init": 1, "call": 1, "index-n": 1, "construct": 1, "record-update": 1,
    "binary": 2, "index": 2, "checked-index": 2, "dict_entry": 2, "if": 3, "slice": 3,
}


def run(path, expected_exit):
    process = subprocess.run(
        [str(ROOT / "build/elisa-proof"), "--json", str(path)],
        capture_output=True, text=True, timeout=120,
    )
    assert process.returncode == expected_exit, (str(path), process.returncode, process.stderr)
    return process.stdout, json.loads(process.stdout)


def check_measurements(text, report):
    measured = report["measurements"]
    assert list(report)[-1] == "measurements", "measurements must be the last section"
    assert measured["format"] == "elisa-proof-measurements-v1"
    assert set(measured) == {"format", "heaviest_functions", *KEYS}, sorted(measured)
    check_heaviest(report)
    assert all(isinstance(measured[key], int) and measured[key] >= 0 for key in KEYS)
    kernel = report["kernel"]
    assert measured["declarations"] == report["summary"]["declarations"]
    assert measured["obligations"] == report["summary"]["obligations"]
    assert measured["certificates"] == len(report["certificates"])
    assert measured["certificate_facts"] == len(kernel["certificate_facts"])
    assert measured["fact_traces"] == len(kernel["fact_traces"])
    assert measured["kernel_nodes"] == len(kernel["nodes"])
    assert measured["kernel_children"] == len(kernel["children"])
    largest = max((goal["kernel_facts_count"] for goal in report["certificates"]), default=0)
    assert measured["largest_certificate_facts"] == largest
    # The byte count covers everything before the section itself.
    assert measured["report_bytes"] == text.index(',"measurements":'), (measured["report_bytes"], text.index(',"measurements":'))


def check_heaviest(report):
    # Recompute the ranking from the goal list: per-name totals, ten largest, first-seen on ties.
    totals = {}
    for goal in report["goals"]:
        entry = totals.setdefault(goal["name"], [0, 0])
        entry[0] += 1
        entry[1] += goal["kernel_facts_count"]
    ranked = sorted(totals.items(), key=lambda item: -item[1][1])[:10]
    expected = [{"name": name, "goal_attempts": count, "certificate_kernel_facts": facts}
                for name, (count, facts) in ranked]
    assert report["measurements"]["heaviest_functions"] == expected, report["measurements"]["heaviest_functions"]


def check_arena(report):
    nodes = report["kernel"]["nodes"]
    children = report["kernel"]["children"]
    for index, node in enumerate(nodes):
        fields = REFERENCE_FIELDS.get(node["kind"], 0)
        for field in ("left", "right", "auxiliary")[:fields]:
            assert node[field] < index, (index, node)
        start, count = node["children_start"], node["children_count"]
        assert start + count <= len(children), (index, node)
        assert all(child < index for child in children[start:start + count]), (index, node)


def main():
    text, verified = run(ROOT / "examples/verified.elisa", 0)
    check_measurements(text, verified)
    check_arena(verified)
    assert verified["replay"]["gaps"] == 0 and verified["replay"]["replayed"] == verified["replay"]["certificates"]
    # Every certificate re-encodes its facts, so a proved source with several goals shares terms.
    assert verified["measurements"]["kernel_nodes_shared"] > 0
    assert verified["measurements"]["control_flow_steps"] > 0 and verified["measurements"]["live_facts_peak"] > 0

    text, library = run(ROOT / "examples/adt_library.elisa", 0)
    check_measurements(text, library)
    assert len(library["measurements"]["heaviest_functions"]) > 1

    text, repeated = run(ROOT / "examples/repeated_index_certificates.elisa", 0)
    check_measurements(text, repeated)
    check_arena(repeated)
    assert repeated["measurements"]["kernel_nodes_shared"] > 0

    # Sharing must never merge quantifiers: the false `forall` stays open beside the true
    # `exists` over the same body, and each proven `exists` replays from its own node.
    text, quantifiers = run(ROOT / "examples/rejected_quantifier_kind_sharing.elisa", 1)
    check_measurements(text, quantifiers)
    check_arena(quantifiers)
    assert quantifiers["status"] == "failed" and quantifiers["replay"]["gaps"] == 0
    goals = quantifiers["goals"]
    forall = [goal for goal in goals if goal["rule"] == "quantifier-forall"]
    exists = [goal for goal in goals if goal["rule"] == "quantifier-exists"]
    assert len(forall) == 2 and not any(goal["proven"] for goal in forall)
    assert len(exists) == 2 and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in exists)
    nodes = quantifiers["kernel"]["nodes"]
    roots = [goal["kernel_goal"] for goal in exists]
    assert roots[0] != roots[1] and all(nodes[root]["operator"] == "exists" for root in roots)
    kinds = sorted(node["operator"] for node in nodes if node["kind"] == "quantifier")
    assert kinds == ["exists", "exists", "forall", "forall"], kinds

    # A source that does not parse still reports a complete, empty measurement section.
    with tempfile.TemporaryDirectory() as directory:
        malformed = Path(directory) / "malformed.elisa"
        malformed.write_text("def broken(:\n    return\n")
        process = subprocess.run(
            [str(ROOT / "build/elisa-proof"), "--json", str(malformed)],
            capture_output=True, text=True, timeout=60,
        )
        assert process.returncode != 0
        report = json.loads(process.stdout)
        check_measurements(process.stdout, report)
        assert report["measurements"]["heaviest_functions"] == []
        assert report["measurements"]["kernel_nodes"] == 0 and report["measurements"]["certificates"] == 0
    print("measurements: schema, report consistency, arena order, and quantifier separation passed")


if __name__ == "__main__":
    main()
