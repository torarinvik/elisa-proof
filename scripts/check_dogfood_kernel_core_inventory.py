#!/usr/bin/env python3
"""Fail-closed exact identity and property inventory gate for kernel-core dogfood."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


DECLARATION_FIELDS = (
    "kind", "name", "line", "requires", "ensures", "verified", "verification_reason",
)
PROPERTY_FIELDS = ("name", "line", "rule", "goal", "proven", "replay_status")


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def fail(message: str) -> None:
    raise ValueError(message)


def verify(root: Path, report_path: Path, inventory_path: Path, slice_name: str) -> None:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("schema") != 1:
        fail("unsupported inventory schema")
    try:
        contract = inventory["slices"][slice_name]
    except KeyError as error:
        fail(f"inventory has no slice {slice_name!r}: {error}")

    for relative, expected in contract["source_files"].items():
        source_path = root / relative
        actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if actual != expected:
            fail(f"source identity mismatch for {relative}: expected {expected}, got {actual}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    source = report.get("source", {})
    expected_source = contract["report_source"]
    fingerprint = source.get("fingerprint", {})
    if (source.get("bytes") != expected_source["bytes"]
            or fingerprint.get("algorithm") != expected_source["fingerprint_algorithm"]
            or fingerprint.get("value") != expected_source["fingerprint"]):
        fail(f"report source identity mismatch for {slice_name}")

    declarations = [
        {field: declaration.get(field) for field in DECLARATION_FIELDS}
        for declaration in report.get("declaration_details", [])
    ]
    if len(declarations) != contract["declaration_count"]:
        fail(f"declaration inventory count mismatch: expected {contract['declaration_count']}, got {len(declarations)}")
    actual_declarations = canonical_digest(declarations)
    if actual_declarations != contract["declaration_inventory_sha256"]:
        fail(f"declaration inventory identity mismatch: {actual_declarations}")

    properties = [
        {field: goal.get(field) for field in PROPERTY_FIELDS}
        for goal in report.get("goals", []) if goal.get("rule") == "goal"
    ]
    if len(properties) != contract["property_count"]:
        fail(f"named property inventory count mismatch: expected {contract['property_count']}, got {len(properties)}")
    actual_properties = canonical_digest(properties)
    if actual_properties != contract["property_inventory_sha256"]:
        fail(f"named property inventory identity mismatch: {actual_properties}")

    declarations_by_name = {}
    for declaration in report.get("declaration_details", []):
        declarations_by_name.setdefault(declaration.get("name"), []).append(declaration)
    for expected in contract["properties"]:
        matches = [item for item in declarations_by_name.get(expected["declaration"], [])
                   if item.get("kind") == "function"]
        if len(matches) != 1:
            fail(f"expected exactly one inventoried function {expected['declaration']!r}")
        declaration = matches[0]
        if (not declaration.get("verified") or declaration.get("verification_reason") != "verified"
                or declaration.get("requires") != int("requires" in expected)
                or declaration.get("ensures") != 1):
            fail(f"inventoried property declaration is missing its checked contract: {expected['declaration']}")
        for clause in (expected.get("requires"), expected.get("ensures")):
            if clause and clause not in "\n".join(
                    (root / path).read_text(encoding="utf-8") for path in contract["source_files"]):
                fail(f"source property clause missing for {expected['declaration']}: {clause}")

    summary = report.get("summary", {})
    if (report.get("status") != "proved" or report.get("verification_state") != "proved"
            or summary.get("proven") != summary.get("obligations")
            or report.get("findings") or report.get("replay", {}).get("gaps") != 0
            or report.get("replay", {}).get("certificates") != report.get("replay", {}).get("replayed")
            or report.get("kernel", {}).get("independent_replay") is not True):
        fail(f"proof/replay admission checks failed for {slice_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="repository root")
    parser.add_argument("--report", type=Path, required=True, help="proof JSON report")
    parser.add_argument("--inventory", type=Path, required=True, help="reviewed inventory manifest")
    parser.add_argument("--slice", choices=("kernel_core", "kernel_core_fixture"), required=True)
    args = parser.parse_args()
    try:
        verify(args.root, args.report, args.inventory, args.slice)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"dogfood inventory failed: {error}", file=sys.stderr)
        return 1
    print(f"dogfood inventory {args.slice}: exact source, declarations, named properties, and replay verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
