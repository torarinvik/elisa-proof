#!/usr/bin/env python3
"""Check the report's v1 compatibility shape and the v2 version marker."""

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def check(instance, schema, name):
    """Evaluate the small JSON Schema keyword subset used by these schemas."""
    if "$ref" in schema:
        referenced = json.loads((SCHEMA_DIR / schema["$ref"]).read_text())
        check(instance, referenced, name)
    for part in schema.get("allOf", []):
        check(instance, part, name)
    condition = schema.get("if")
    if condition is not None:
        try:
            check(instance, condition, name)
        except AssertionError:
            pass
        else:
            check(instance, schema.get("then", {}), name)
    expected = schema.get("type")
    if expected == "object":
        assert isinstance(instance, dict), f"{name}: expected object"
        for key in schema.get("required", []):
            assert key in instance, f"{name}: missing required property {key}"
        for key, child_schema in schema.get("properties", {}).items():
            if key in instance:
                check(instance[key], child_schema, f"{name}.{key}")
    elif expected == "array":
        assert isinstance(instance, list), f"{name}: expected array"
        assert len(instance) <= schema.get("maxItems", len(instance)), f"{name}: too many items"
    elif expected == "string":
        assert isinstance(instance, str), f"{name}: expected string"
    elif expected == "integer":
        assert isinstance(instance, int) and not isinstance(instance, bool), f"{name}: expected integer"
        assert instance >= schema.get("minimum", instance), f"{name}: below minimum"
    if "enum" in schema:
        assert instance in schema["enum"], f"{name}: unexpected value {instance!r}"
    if "const" in schema:
        assert instance == schema["const"], f"{name}: expected {schema['const']!r}"


def check_report_invariants(report, name):
    """Check count and verdict relationships that JSON Schema cannot express arithmetically."""
    summary = report["summary"]
    replay = report["replay"]
    counters = (
        summary["obligations"], summary["proven"], summary["unproven"],
        summary["failed"], summary["finding_count"], replay["certificates"],
        replay["replayed"], replay["gaps"],
    )
    assert all(type(value) is int and value >= 0 for value in counters), (
        f"{name}: invalid summary or replay counts")
    obligations = summary["obligations"]
    proven = summary["proven"]
    unproven = summary["unproven"]
    assert proven <= obligations and unproven == obligations - proven, (
        f"{name}: inconsistent proven/unproven obligation counts")
    assert summary["finding_count"] == len(report["findings"]), (
        f"{name}: finding_count does not match findings")
    assert summary["failed"] == len(report["findings"]), (
        f"{name}: failed does not match finding count")
    if report["status"] == "proved":
        assert proven == obligations and unproven == 0, (
            f"{name}: proved report contains unproven obligations")
        assert replay["gaps"] == 0 and replay["replayed"] == replay["certificates"], (
            f"{name}: proved report does not have complete certificate replay")


def main():
    v1 = json.loads((SCHEMA_DIR / "elisa-proof-v1.json").read_text())
    v2 = json.loads((SCHEMA_DIR / "elisa-proof-v2.json").read_text())
    # A representative report captured before protocol_version was emitted.
    old_report = {
        "status": "proved", "verification_state": "proved", "engine_state": "proved",
        "source": {"bytes": 12, "fingerprint": {"algorithm": "fnv1a32", "value": 123}},
        "summary": {"declarations": 1, "obligations": 1, "proven": 1,
                    "unproven": 0, "failed": 0, "finding_count": 0},
        "replay": {"certificates": 1, "replayed": 1, "gaps": 0},
        "kernel": {"format": "elisa-proof-kernel-v1", "independent_replay": True,
                   "nodes": [], "children": []},
        "findings": [], "goals": [],
    }
    check(old_report, v1, "v1 report")
    check_report_invariants(old_report, "v1 report")
    assert "protocol_version" not in old_report
    current_report = dict(old_report, protocol_version=2)
    check(current_report, v2, "v2 report")
    incompatible = dict(old_report, protocol_version=1)
    try:
        check(incompatible, v2, "wrong-version report")
    except AssertionError:
        pass
    else:
        raise AssertionError("v2 schema accepted protocol_version 1")
    emitted = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples/loop_invariants_compile.elisa")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert emitted.returncode == 0, emitted.stderr
    current_report = json.loads(emitted.stdout)
    check(current_report, v2, "emitted v2 report")
    check_report_invariants(current_report, "emitted v2 report")
    assert current_report["protocol_version"] == 2

    # Current rejected reports use engine_state="open"; the compatibility schema must
    # accept this real producer value as well as successful reports.
    rejected = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples/rejected_unsigned_local_states.elisa")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert rejected.returncode == 1, rejected.stderr
    rejected_report = json.loads(rejected.stdout)
    assert rejected_report["engine_state"] == "open", rejected_report["engine_state"]
    check(rejected_report, v2, "emitted rejected v2 report")
    check_report_invariants(rejected_report, "emitted rejected v2 report")

    # Adversarial mutations preserve JSON shape while contradicting a successful verdict.
    for field, mutate in (
        ("verification_state", lambda row: row.update(verification_state="unknown")),
        ("engine_state", lambda row: row.update(engine_state="open")),
        ("replay-gap", lambda row: row["replay"].update(gaps=1)),
        ("replay-counts", lambda row: row["replay"].update(replayed=row["replay"]["replayed"] - 1)),
        ("obligations", lambda row: row["summary"].update(unproven=1)),
        ("findings", lambda row: row["findings"].append({"kind": "forged"})),
        ("kernel", lambda row: row["kernel"].update(independent_replay=False)),
    ):
        adversarial = json.loads(json.dumps(current_report))
        mutate(adversarial)
        try:
            check(adversarial, v2, f"adversarial {field}")
            check_report_invariants(adversarial, f"adversarial {field}")
        except AssertionError:
            continue
        raise AssertionError(f"proved report accepted inconsistent {field}")
    print("v1 compatibility and an emitted v2 report validated")


if __name__ == "__main__":
    main()
