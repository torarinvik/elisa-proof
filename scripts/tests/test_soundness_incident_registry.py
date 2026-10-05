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
    lambda item: item["affected_products"][0].update(kind=[]),
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

# End-to-end invalidation policy: an old cache entry or declaration artifact is affected only
# when both its exact product identity and the exact semantic rule/version match a confirmed
# incident. Artifact/cache schema labels are not semantic identities and cannot cause a false hit
# or false invalidation by themselves.
old_cache = {
    "kind": "report-cache", "identity": "sha256:old-report-key", "sha256": "d" * 64,
    "schema": "report-cache-v3", "rule_semantics": [{"rule": "kernel.linear-ineq", "version": "1"}],
}
old_artifact = {
    "kind": "declaration-artifact", "identity": "calculate:artifact-id", "sha256": "e" * 64,
    "schema": "declaration-artifact-v2", "rule_semantics": [{"rule": "kernel.linear-ineq", "version": "1"}],
}
assert not registry.product_is_semantically_affected(EMPTY, old_cache)
assert not registry.product_is_semantically_affected(EMPTY, old_artifact)

# Schema-only migration remains semantically neutral when no incident identifies the rule.
schema_only_cache = {**old_cache, "schema": "report-cache-v4"}
assert not registry.product_is_semantically_affected(EMPTY, schema_only_cache)

confirmed = {
    "schema": registry.SCHEMA,
    "incidents": [{
        **VALID_INCIDENT,
        "id": "confirmed-linear-inequality-bug",
        "rule_semantics": {"rule": "kernel.linear-ineq", "version": "1"},
        "affected_products": [
            {"kind": old_cache["kind"], "identity": old_cache["identity"], "sha256": old_cache["sha256"]},
            {"kind": old_artifact["kind"], "identity": old_artifact["identity"], "sha256": old_artifact["sha256"]},
        ],
    }],
}
assert registry.validate(confirmed) == []
assert registry.product_is_semantically_affected(confirmed, old_cache)
assert registry.product_is_semantically_affected(confirmed, old_artifact)
# A package/schema-only update does not erase a semantic incident; only a new rule-semantics
# version escapes it. Likewise, the same rule version on another exact product is not overmatched.
assert registry.product_is_semantically_affected(confirmed, schema_only_cache)
fixed_cache = {**old_cache, "rule_semantics": [{"rule": "kernel.linear-ineq", "version": "2"}]}
assert not registry.product_is_semantically_affected(confirmed, fixed_cache)
other_cache = {**old_cache, "identity": "sha256:other-report-key"}
assert not registry.product_is_semantically_affected(confirmed, other_cache)
wrong_digest = {**old_cache, "sha256": "f" * 64}
assert not registry.product_is_semantically_affected(confirmed, wrong_digest)
malformed_product = {**old_cache, "kind": []}
try:
    registry.product_is_semantically_affected(confirmed, malformed_product)
except ValueError as error:
    assert "malformed" in str(error)
else:
    raise AssertionError("malformed product identity was allowed through the invalidation gate")

try:
    registry.product_is_semantically_affected({"schema": "unknown", "incidents": []}, old_cache)
except ValueError as error:
    assert "invalid soundness incident registry" in str(error)
else:
    raise AssertionError("invalid registry was allowed to authorize a cache/artifact reuse")

print("soundness incident registry: strict records and exact semantic product invalidation passed")
