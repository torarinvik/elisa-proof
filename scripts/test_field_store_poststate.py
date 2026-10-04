#!/usr/bin/env python3
"""Guard field post-state substitution and reject stale pre-state claims."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/field_store_poststate_probe.elisa"
PROVER = ROOT / "build/elisa-proof"

POSITIVE = {
    "scalar_field_store_updates_poststate",
    "nullable_field_store_updates_poststate",
}
NEGATIVE = {
    "rejected_scalar_field_without_write",
    "rejected_nullable_field_without_write",
    "rejected_branch_write_claims_old_value_preserved",
    "rejected_loop_write_claims_old_value_preserved",
}


def main() -> int:
    result = subprocess.run(
        [str(PROVER), "--json", str(FIXTURE)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 1:
        raise AssertionError(
            f"expected intentional negative controls to fail with status 1, got {result.returncode}: "
            f"{result.stderr[-2000:]}"
        )
    report = json.loads(result.stdout)
    assert report["status"] == "failed"
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]

    functions = {
        declaration["name"]: declaration
        for declaration in report["declaration_details"]
        if declaration["kind"] == "function"
    }
    for name in POSITIVE:
        assert functions[name]["verified"], f"field post-state was not proved: {name}"
    for name in NEGATIVE:
        assert not functions[name]["verified"], f"invalid field post-state claim was accepted: {name}"

    goals = report["goals"]
    for name in NEGATIVE:
        assert any(goal["name"] == name and not goal["proven"] for goal in goals), (
            f"negative field control had no rejected postcondition: {name}"
        )
        assert any(
            finding["name"] == name
            and finding["kind"] == "ensure-unproven"
            and finding["status"] in ("disproved", "unknown")
            for finding in report["findings"]
        ), f"negative field control was refused for an unrelated reason: {name}"
    print("mutable field post-state proofs and stale-state controls passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, json.JSONDecodeError) as error:
        print(f"field store post-state regression failed: {error}", file=sys.stderr)
        raise SystemExit(1)
