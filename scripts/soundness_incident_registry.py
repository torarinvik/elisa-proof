#!/usr/bin/env python3
"""Validate the versioned registry of confirmed proof soundness incidents.

This gate validates declarations and exact product identities. It does not decide which
products were affected; each incident requires an explicit, evidence-backed classification.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = "elisa-proof-soundness-incident-registry-v1"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PRODUCT_KINDS = {"proof-product", "portable-package", "report-cache", "declaration-artifact"}


def _object(value, required, optional=()):
    return (isinstance(value, dict) and required <= value.keys()
            and value.keys() <= required | set(optional))


def validate(registry):
    """Return a list of validation errors; unknown fields fail closed."""
    errors = []
    if not _object(registry, {"schema", "incidents"}) or registry.get("schema") != SCHEMA:
        return [f"registry must use schema {SCHEMA} and contain only schema/incidents"]
    incidents = registry["incidents"]
    if not isinstance(incidents, list):
        return ["incidents must be an array"]
    seen = set()
    required = {"id", "rule_semantics", "affected_products", "reproducer", "evidence",
                "trust_boundary", "downstream_theorem_impact", "containment", "fix"}
    for index, incident in enumerate(incidents):
        prefix = f"incidents[{index}]"
        if not _object(incident, required):
            errors.append(f"{prefix} has missing or unknown fields")
            continue
        incident_id = incident["id"]
        if not isinstance(incident_id, str) or not IDENTIFIER.fullmatch(incident_id):
            errors.append(f"{prefix}.id is invalid")
        elif incident_id in seen:
            errors.append(f"{prefix}.id is duplicated")
        else:
            seen.add(incident_id)
        semantics = incident["rule_semantics"]
        if not _object(semantics, {"rule", "version"}) or not all(
            isinstance(semantics.get(key), str) and semantics[key].strip()
            for key in ("rule", "version")
        ):
            errors.append(f"{prefix}.rule_semantics must name a rule and semantic version")
        products = incident["affected_products"]
        if not isinstance(products, list) or not products:
            errors.append(f"{prefix}.affected_products must identify at least one exact product")
        else:
            for product_index, product in enumerate(products):
                product_prefix = f"{prefix}.affected_products[{product_index}]"
                if not _object(product, {"kind", "identity", "sha256"}):
                    errors.append(f"{product_prefix} has missing or unknown fields")
                    continue
                if not isinstance(product["kind"], str) or product["kind"] not in PRODUCT_KINDS:
                    errors.append(f"{product_prefix}.kind is unsupported")
                if not isinstance(product["identity"], str) or not product["identity"].strip():
                    errors.append(f"{product_prefix}.identity is required")
                if not isinstance(product["sha256"], str) or not SHA256.fullmatch(product["sha256"]):
                    errors.append(f"{product_prefix}.sha256 must be lowercase SHA-256")
        for field in ("reproducer", "evidence"):
            value = incident[field]
            if not _object(value, {"reference", "sha256"}) or not all(
                isinstance(value.get(key), str) and value[key].strip()
                for key in ("reference", "sha256")
            ) or not SHA256.fullmatch(value.get("sha256", "") if isinstance(value, dict) else ""):
                errors.append(f"{prefix}.{field} must have a reference and lowercase SHA-256")
        for field in ("trust_boundary", "downstream_theorem_impact", "containment"):
            if not isinstance(incident[field], str) or not incident[field].strip():
                errors.append(f"{prefix}.{field} must be documented")
        fix = incident["fix"]
        if not _object(fix, {"commit", "rule_semantics_version"}) or not all(
            isinstance(fix.get(key), str) and fix[key].strip()
            for key in ("commit", "rule_semantics_version")
        ):
            errors.append(f"{prefix}.fix must name a commit and new rule semantics version")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", nargs="?", default=str(Path(__file__).with_name("soundness_incidents.json")))
    args = parser.parse_args()
    try:
        with open(args.registry, encoding="utf-8") as source:
            registry = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"soundness incident registry: cannot read JSON: {error}", file=sys.stderr)
        return 2
    errors = validate(registry)
    if errors:
        for error in errors:
            print(f"soundness incident registry: {error}", file=sys.stderr)
        return 1
    print(f"soundness incident registry valid: {len(registry['incidents'])} confirmed incidents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
