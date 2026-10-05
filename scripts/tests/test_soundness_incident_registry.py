#!/usr/bin/env python3
"""Structural fail-closed controls for the confirmed soundness incident registry."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/soundness_incident_registry.py"
spec = importlib.util.spec_from_file_location("soundness_incident_registry", MODULE)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)

EMPTY = {"schema": registry.SCHEMA, "incidents": []}
VALID_INCIDENT = {
    "id": "example-controlled-test",
    "rule_semantics": {"rule": "test-rule", "version": "1"},
    "affected_products": [{"kind": "proof-product", "identity": "product identity",
                           "sha256": "a" * 64}],
    "reproducer": {"reference": "fixture.elisa", "sha256": "b" * 64},
    "evidence": {"reference": "evidence.md", "sha256": "c" * 64},
    "trust_boundary": "test-only",
    "downstream_theorem_impact": "test-only",
    "containment": "test-only",
    "fix": {"commit": "deadbeef", "rule_semantics_version": "2"},
}


assert registry.validate(EMPTY) == []
assert registry.validate({"schema": "unknown", "incidents": []})
assert registry.validate({**EMPTY, "unexpected": True})
assert registry.validate({"schema": registry.SCHEMA, "incidents": {}})
assert registry.validate({"schema": registry.SCHEMA, "incidents": [VALID_INCIDENT]}) == []
assert registry.validate({"schema": registry.SCHEMA, "incidents": [VALID_INCIDENT, VALID_INCIDENT]})

for field in ("rule_semantics", "affected_products", "reproducer", "evidence",
              "trust_boundary", "downstream_theorem_impact", "containment", "fix"):
    malformed = dict(VALID_INCIDENT)
    del malformed[field]
    assert registry.validate({"schema": registry.SCHEMA, "incidents": [malformed]}), field

for mutate in (
    lambda item: item["affected_products"].clear(),
    lambda item: item["affected_products"][0].update(sha256="not-a-digest"),
    lambda item: item["affected_products"][0].update(kind="unknown"),
    lambda item: item["evidence"].update(sha256="not-a-digest"),
    lambda item: item.update(unsupported_claim=True),
):
    malformed = {**VALID_INCIDENT,
                 "affected_products": [dict(VALID_INCIDENT["affected_products"][0])],
                 "reproducer": dict(VALID_INCIDENT["reproducer"]),
                 "evidence": dict(VALID_INCIDENT["evidence"])}
    mutate(malformed)
    assert registry.validate({"schema": registry.SCHEMA, "incidents": [malformed]})

assert registry.validate(__import__("json").loads((ROOT / "scripts/soundness_incidents.json").read_text())) == []
print("soundness incident registry: empty registry and strict confirmed-record validation passed")
