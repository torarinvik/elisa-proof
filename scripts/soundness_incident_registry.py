#!/usr/bin/env python3
"""Validate confirmed incidents and unresolved soundness reports.

Confirmed incidents require evidence-backed exact product identities. Reports missing those
identities stay visible and block product reuse classification until resolved.
"""
import argparse
import re
import sys
from pathlib import Path
from strict_json import loads as strict_json_loads

SCHEMA = "elisa-proof-soundness-incident-registry-v2"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GIT_COMMIT = re.compile(r"[0-9a-fA-F]{7,64}\Z")
PRODUCT_KINDS = {"proof-product", "portable-package", "report-cache", "declaration-artifact"}


def _object(value, required, optional=()):
    return (isinstance(value, dict) and required <= value.keys()
            and value.keys() <= required | set(optional))


def validate(registry):
    """Return a list of validation errors; unknown fields fail closed."""
    errors = []
    if not isinstance(registry, dict):
        return ["registry must be a JSON object"]
    if not _object(registry, {"schema", "incidents", "unclassified_reports"}) \
            or registry.get("schema") != SCHEMA:
        return [f"registry must use schema {SCHEMA} and contain schema/incidents/unclassified_reports"]
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
        else:
            if not GIT_COMMIT.fullmatch(fix["commit"]):
                errors.append(f"{prefix}.fix.commit must be a hexadecimal Git commit ID")
            if isinstance(semantics, dict) and isinstance(semantics.get("version"), str) \
                    and fix["rule_semantics_version"] == semantics["version"]:
                errors.append(f"{prefix}.fix must advance the affected rule semantics version")
    unclassified = registry["unclassified_reports"]
    if not isinstance(unclassified, list):
        errors.append("unclassified_reports must be an array")
    else:
        for index, report in enumerate(unclassified):
            prefix = f"unclassified_reports[{index}]"
            if not _object(report, {"id", "status", "summary", "reference"}):
                errors.append(f"{prefix} has missing or unknown fields")
                continue
            report_id = report["id"]
            if not isinstance(report_id, str) or not IDENTIFIER.fullmatch(report_id):
                errors.append(f"{prefix}.id is invalid")
            elif report_id in seen:
                errors.append(f"{prefix}.id is duplicated")
            else:
                seen.add(report_id)
            if report["status"] != "exact-product-identity-incomplete":
                errors.append(f"{prefix}.status is unsupported")
            for field in ("summary", "reference"):
                if not isinstance(report[field], str) or not report[field].strip():
                    errors.append(f"{prefix}.{field} is required")
    return errors


def registry_allows_unqualified_reuse(registry) -> bool:
    """Whether a registry fully clears products lacking per-rule semantic metadata.

    This deliberately authorizes reuse only for an explicitly complete, empty ledger. A caller
    with exact product/rule identity should instead use ``product_is_semantically_affected``.
    """
    return not validate(registry) and isinstance(registry, dict) \
        and "unclassified_reports" in registry and not registry["incidents"] \
        and not registry["unclassified_reports"]


def product_is_semantically_affected(registry, product):
    """Return whether a confirmed incident invalidates this exact product.

    Product presentation/schema fields and caller-supplied rule lists cannot clear an exact
    affected-product match. A binary or artifact digest identifies the whole product; per-rule
    metadata is useful for triage but must not be an incomplete escape hatch. Invalid registry or
    product metadata raises rather than allowing a cache/artifact hit. Any unresolved incident
    report also blocks this decision until exact impact or a reviewed exclusion is recorded.
    """
    errors = validate(registry)
    if errors:
        raise ValueError("invalid soundness incident registry: " + "; ".join(errors))
    if "unclassified_reports" not in registry:
        raise ValueError("soundness registry lacks unresolved-report coverage; reuse is not authorized")
    if registry.get("unclassified_reports"):
        raise ValueError("unclassified soundness reports prevent product reuse classification")
    required = {"kind", "identity", "sha256"}
    optional = {"schema", "label", "rule_semantics"}
    if not _object(product, required, optional):
        raise ValueError("product semantic identity has missing or unknown fields")
    if not isinstance(product["kind"], str) or product["kind"] not in PRODUCT_KINDS \
            or not isinstance(product["identity"], str) \
            or not product["identity"].strip() or not isinstance(product["sha256"], str) \
            or not SHA256.fullmatch(product["sha256"]):
        raise ValueError("product semantic identity is malformed")
    if "rule_semantics" in product:
        rules = product["rule_semantics"]
        if not isinstance(rules, list) or not all(
            _object(rule, {"rule", "version"})
            and isinstance(rule["rule"], str) and rule["rule"].strip()
            and isinstance(rule["version"], str) and rule["version"].strip()
            for rule in rules
        ):
            raise ValueError("product rule_semantics must contain exact rule/version identities")

    product_identity = (product["kind"], product["identity"], product["sha256"])
    for incident in registry["incidents"]:
        incident_products = {
            (item["kind"], item["identity"], item["sha256"])
            for item in incident["affected_products"]
        }
        if product_identity in incident_products:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", nargs="?", default=str(Path(__file__).with_name("soundness_incidents.json")))
    args = parser.parse_args()
    try:
        registry = strict_json_loads(Path(args.registry).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        print(f"soundness incident registry: cannot read JSON: {error}", file=sys.stderr)
        return 2
    errors = validate(registry)
    if errors:
        for error in errors:
            print(f"soundness incident registry: {error}", file=sys.stderr)
        return 1
    print(f"soundness incident registry valid: {len(registry['incidents'])} confirmed incidents, "
          f"{len(registry['unclassified_reports'])} reports awaiting exact product identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
