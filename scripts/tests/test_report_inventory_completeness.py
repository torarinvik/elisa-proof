#!/usr/bin/env python3
"""Exercise report inventories through the shared admission boundary and real CLI."""
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
INVARIANT_HARNESS = Path(os.environ.get("ELISA_REPORT_INVENTORY_HARNESS", ""))


def run_report(source: Path) -> tuple[int, dict]:
    result = subprocess.run(
        [str(PROOF), "--json", str(source)], capture_output=True, text=True, timeout=120
    )
    report = json.loads(result.stdout)
    expected_exit = 0 if report.get("status") == "proved" else 1
    assert result.returncode == expected_exit, (
        source.name, result.returncode, report.get("status"), result.stderr
    )
    return result.returncode, report


def check_emitted_inventory(report: dict, *, proved: bool) -> None:
    summary = report["summary"]
    declarations = report["declaration_details"]
    goals = report["goals"]
    findings = report["findings"]
    certificates = report["certificates"]

    # These are properties of this emitted report, not a substitute admission decision:
    # the actual verifier has already made the decision before returning its exit status.
    assert summary["declarations"] == len(declarations)
    # Some unsupported source checks create a failed obligation/finding without a goal
    # certificate attempt. The source-level obligation count is authoritative; goal rows are
    # the subset that received an explicit proof attempt.
    assert summary["obligations"] >= len(goals)
    assert summary["proven"] + summary["unproven"] == summary["obligations"]
    assert summary["failed"] == len(findings)
    assert summary["finding_count"] == len(findings)
    successful = [goal for goal in goals if goal["proven"]]
    assert len(successful) == summary["proven"]
    assert sum(not goal["proven"] for goal in goals) <= summary["unproven"]
    assert len(certificates) == report["replay"]["certificates"]
    assert report["replay"]["replayed"] <= report["replay"]["certificates"]
    if proved:
        assert report["status"] == "proved"
        assert report["verification_state"] == "proved"
        assert not findings
        assert summary["proven"] == summary["obligations"]
        assert report["replay"]["gaps"] == 0
        assert report["replay"]["replayed"] == report["replay"]["certificates"]
        assert all(goal["replay_status"] == "replayed" for goal in successful)
    else:
        assert report["status"] != "proved"
        assert report["verification_state"] in ("unknown", "unsupported", "disproved")


def main() -> None:
    assert PROOF.is_file(), f"proof executable not found: {PROOF}"
    assert INVARIANT_HARNESS.is_file(), (
        "test runner must provide the executable compiled from "
        "examples/report_invariants_runtime.elisa"
    )

    # The Elisa harness imports the exact report_invariants module used by CLI admission,
    # mutates its report rows/counters, and returns nonzero if any mutation remains admitted.
    mutation = subprocess.run([str(INVARIANT_HARNESS)], capture_output=True, timeout=30)
    assert mutation.returncode == 0, (
        "R-004 bypass characterization failed: the harness did not reproduce both "
        "report-owned scheduling-status and aggregate-offset bypasses: "
        f"exit={mutation.returncode}, stderr={mutation.stderr[:500]!r}"
    )

    code, verified = run_report(ROOT / "examples/verified.elisa")
    assert code == 0
    check_emitted_inventory(verified, proved=True)
    assert [(row["kind"], row["name"], row["line"]) for row in verified["declaration_details"]] == [
        ("function", "successor", 3),
        ("function", "prove_nonnegative", 9),
        ("function", "prove_reflexive", 15),
    ]

    # Nested module and member summaries must follow the same preorder as the admitted AST.
    code, nested = run_report(ROOT / "examples/global_constant_module.elisa")
    assert code == 0
    check_emitted_inventory(nested, proved=True)
    assert [(row["kind"], row["name"]) for row in nested["declaration_details"]] == [
        ("module", "LocalConstants"),
        ("const", "LIMIT"),
        ("function", "uses_local_limit"),
    ]

    # A well-formed but unfinished proof remains a supported partial outcome, never `proved`.
    code, incomplete = run_report(ROOT / "examples/tactic_repair_target.elisa")
    assert code == 1
    check_emitted_inventory(incomplete, proved=False)
    assert incomplete["summary"]["unproven"] > 0
    assert incomplete["verification_state"] in ("unknown", "unsupported")

    # Unsupported source analysis is also distinct from proof success and remains visible.
    code, unsupported = run_report(ROOT / "examples/unsupported_computed_write_place.elisa")
    assert code == 1
    check_emitted_inventory(unsupported, proved=False)
    assert unsupported["verification_state"] == "unsupported"
    assert any(finding["status"] == "unsupported" for finding in unsupported["findings"])

    print("R-004 audit: both proposed-gate bypasses reproduced; existing CLI inventory checks passed (source completeness remains open)")


if __name__ == "__main__":
    main()
