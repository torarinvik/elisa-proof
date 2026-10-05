#!/usr/bin/env python3
"""Check the report's v1 compatibility shape and the v2 version marker."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"


def check(instance, schema, name):
    """Evaluate the small JSON Schema keyword subset used by these schemas."""
    if "$ref" in schema:
        referenced = json.loads((SCHEMA_DIR / schema["$ref"]).read_text())
        check(instance, referenced, name)
    for part in schema.get("allOf", []):
        check(instance, part, name)
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
    elif expected == "string":
        assert isinstance(instance, str), f"{name}: expected string"
    elif expected == "integer":
        assert isinstance(instance, int) and not isinstance(instance, bool), f"{name}: expected integer"
        assert instance >= schema.get("minimum", instance), f"{name}: below minimum"
    if "enum" in schema:
        assert instance in schema["enum"], f"{name}: unexpected value {instance!r}"
    if "const" in schema:
        assert instance == schema["const"], f"{name}: expected {schema['const']!r}"


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
    emitter = (ROOT / "src/app/report_output_integrated_helpers.elisa").read_text()
    escaped_quote = chr(92) + '"'
    assert escaped_quote + 'protocol_version' in emitter and ':2,' + escaped_quote + 'status' in emitter
    print("v1 compatibility and v2 version marker validated")


if __name__ == "__main__":
    main()
