#!/usr/bin/env python3
"""Exercise report inventories through the shared admission boundary and real CLI."""
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
INVARIANT_HARNESS = Path(os.environ.get("ELISA_REPORT_INVENTORY_HARNESS", ""))
BRANCH_HARNESS = Path(os.environ.get("ELISA_ASSERT_BY_BRANCH_HARNESS", ""))


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
    inventory = report["source_obligation_inventory"]
    assert inventory["coverage"] == "partial"
    assert inventory["whole_program"] is False
    assert "Boolean-literal assert-by" in inventory["supported_subset"]
    assert "direct if/match branches" in inventory["supported_subset"]
    assert "nested branch and scoped bodies are unsupported" in inventory["supported_subset"]
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
    assert BRANCH_HARNESS.is_file(), (
        "test runner must provide the executable compiled from "
        "examples/source_assert_by_branch_inventory_runtime.elisa"
    )

    # The Elisa harness imports the exact report_invariants module used by CLI admission,
    # retains source declarations outside the mutable report, and checks both an intact
    # positive control and coordinated source-report deletion of a required postcondition.
    mutation = subprocess.run([str(INVARIANT_HARNESS)], capture_output=True, timeout=30)
    assert mutation.returncode == 0, (
        "R-004 source-derived admission regression failed: the harness did not accept "
        "the positive control and reject the deliberately omitted source obligation: "
        f"exit={mutation.returncode}, stderr={mutation.stderr[:500]!r}"
    )
    branch_mutations = subprocess.run([str(BRANCH_HARNESS)], capture_output=True, timeout=30)
    assert branch_mutations.returncode == 0, (
        "R-004 branch source-identity regression failed: the harness did not accept valid "
        "if/match branches and reject omission, duplication, false claims, wrong owners, "
        "wrong-branch substitution, bad offsets, and unsupported nested scopes: "
        f"exit={branch_mutations.returncode}, stderr={branch_mutations.stderr[:500]!r}"
    )

    # Exercise the production CLI gate with a source function inside the explicitly supported
    # subset, independently of the hand-built mutation report in the native harness.
    code, source_control = run_report(ROOT / "examples/source_obligation_inventory_positive.elisa")
    assert code == 0
    check_emitted_inventory(source_control, proved=True)
    assert any(
        goal["name"] == "source_inventory_positive"
        and goal["rule"] == "goal"
        and goal["proven"]
        for goal in source_control["goals"]
    )
    literal_goal = next(
        goal for goal in source_control["goals"]
        if goal["name"] == "source_inventory_literal_postcondition" and goal["rule"] == "goal"
    )
    assert literal_goal["rule"] == "goal" and literal_goal["proven"]
    assert literal_goal["replay_status"] == "replayed"
    assert literal_goal["goal"]["right"]["line"] == 8
    positive_postconditions = [
        goal for goal in source_control["goals"]
        if goal["name"] in ("source_inventory_positive", "source_inventory_literal_postcondition")
        and goal["rule"] == "goal"
    ]
    assert len(positive_postconditions) == 2
    assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in positive_postconditions)

    # Nested module functions are traversed by the proof checker. Until source identities
    # include namespace paths, their postconditions must be recorded as unsupported by the
    # independent inventory rather than disappearing and allowing a proved whole-file result.
    code, nested_literal = run_report(ROOT / "examples/source_obligation_inventory_nested_scope.elisa")
    assert code == 1
    check_emitted_inventory(nested_literal, proved=False)
    nested_inventory_findings = [
        finding for finding in nested_literal["findings"]
        if finding["kind"] == "source-obligation-inventory"
    ]
    assert nested_inventory_findings
    assert nested_inventory_findings[0]["status"] == "unsupported"
    assert nested_literal["verification_state"] == "unsupported"

    # `ensures` is the plural spelling of the same source construct and must receive an
    # independently inventoried, replayed source obligation as well.
    code, plural = run_report(ROOT / "examples/source_obligation_inventory_plural_ensures.elisa")
    assert code == 0
    check_emitted_inventory(plural, proved=True)
    plural_goal = next(
        goal for goal in plural["goals"]
        if goal["name"] == "source_inventory_plural_ensures" and goal["rule"] == "goal"
    )
    assert plural_goal["proven"] and plural_goal["replay_status"] == "replayed"

    # A false result==7 postcondition after returning 8 remains visible and makes the CLI
    # reject the file. In particular, this source cannot disappear into a vacuous empty
    # inventory and produce `proved`.
    code, mismatched = run_report(ROOT / "examples/source_obligation_inventory_mismatched_return.elisa")
    assert code == 1
    check_emitted_inventory(mismatched, proved=False)
    assert mismatched["summary"]["obligations"] > 0
    assert mismatched["summary"]["unproven"] > 0 or mismatched["summary"]["failed"] > 0
    mismatch_goals = [
        goal for goal in mismatched["goals"]
        if goal["name"] == "source_inventory_mismatched_return" and goal["rule"] == "goal"
    ]
    assert mismatch_goals and all(not goal["proven"] for goal in mismatch_goals)
    mismatch_goal = mismatch_goals[0]
    assert mismatch_goal["replay_status"] != "replayed"
    assert mismatch_goal["goal"]["left"]["value"] == 8
    assert mismatch_goal["goal"]["right"]["value"] == 7

    # Boolean-literal assert-by goals and assert steps form the next bounded, source-derived
    # family. Both source obligations must replay independently.
    code, assert_by_positive = run_report(ROOT / "examples/source_obligation_assert_by_positive.elisa")
    assert code == 0
    check_emitted_inventory(assert_by_positive, proved=True)
    assert_by_goals = [
        goal for goal in assert_by_positive["goals"]
        if goal["name"] == "source_assert_by_inventory_positive" and goal["rule"] == "goal"
    ]
    assert sorted(goal["line"] for goal in assert_by_goals) == [3, 4]
    assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in assert_by_goals)
    assert all(goal["goal"]["kind"] == "bool" and goal["goal"]["value"] is True for goal in assert_by_goals)

    code, assert_by_false = run_report(ROOT / "examples/source_obligation_assert_by_false.elisa")
    assert code == 1
    check_emitted_inventory(assert_by_false, proved=False)
    assert assert_by_false["summary"]["obligations"] > 0
    false_goal = next(
        goal for goal in assert_by_false["goals"]
        if goal["name"] == "source_assert_by_inventory_false"
        and goal["line"] == 3 and goal["rule"] == "goal"
    )
    assert not false_goal["proven"]
    assert false_goal["goal"]["kind"] == "bool" and false_goal["goal"]["value"] is False
    assert assert_by_false["summary"]["unproven"] > 0 or assert_by_false["summary"]["failed"] > 0

    # Branch body targets use the enclosing top-level function identity plus their exact
    # imported literal offset. Both if arms and both match arms must remain independently
    # covered, even when the branch propositions have the same value.
    code, branch_assert_by = run_report(ROOT / "examples/source_obligation_assert_by_branches.elisa")
    assert code == 0
    check_emitted_inventory(branch_assert_by, proved=True)
    branch_goals = [
        goal for goal in branch_assert_by["goals"]
        if goal["name"] == "source_assert_by_branches" and goal["rule"] == "goal"
    ]
    assert len(branch_goals) == 8
    assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in branch_goals)
    assert all(goal["goal"]["kind"] == "bool" and goal["goal"]["value"] is True for goal in branch_goals)

    code, branch_false = run_report(ROOT / "examples/source_obligation_assert_by_branch_false.elisa")
    assert code == 1
    check_emitted_inventory(branch_false, proved=False)
    false_branch_targets = [
        goal for goal in branch_false["goals"]
        if goal["name"] == "source_assert_by_branch_false" and goal["line"] == 4 and goal["rule"] == "goal"
    ]
    assert false_branch_targets
    assert all(not goal["proven"] for goal in false_branch_targets)
    assert any(goal["goal"]["kind"] == "bool" and goal["goal"]["value"] is False for goal in false_branch_targets)

    # The ordinary checker replays these equality goals. They are outside the literal-only
    # source inventory slice, so the report stays explicitly partial rather than claiming
    # whole-program source completeness or rejecting already replayed proofs.
    code, nonliteral_assert_by = run_report(ROOT / "examples/source_obligation_assert_by_nonliteral.elisa")
    assert code == 0
    check_emitted_inventory(nonliteral_assert_by, proved=True)
    nonliteral_goals = [
        goal for goal in nonliteral_assert_by["goals"]
        if goal["name"] == "source_assert_by_inventory_nonliteral" and goal["rule"] == "goal"
    ]
    assert len(nonliteral_goals) == 2
    assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in nonliteral_goals)

    # Namespace traversal must retain assert-by obligations, but bare-name report identities
    # are insufficient to soundly match nested declarations, so admission fails closed.
    code, module_assert_by = run_report(ROOT / "examples/source_obligation_assert_by_module.elisa")
    assert code == 1
    check_emitted_inventory(module_assert_by, proved=False)
    source_inventory_findings = [
        finding for finding in module_assert_by["findings"]
        if finding["kind"] == "source-obligation-inventory"
    ]
    assert source_inventory_findings
    assert source_inventory_findings[-1]["status"] == "unsupported"
    assert module_assert_by["verification_state"] == "unsupported"

    code, verified = run_report(ROOT / "examples/verified.elisa")
    # Legacy nonliteral goals stay checker/replay-owned while the source inventory identifies
    # itself as partial; this slice must not turn an out-of-scope proposition into a regression.
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

    print("R-004 slices: direct if/match branch BoolLit assert-by inventory validated; false goals remain open; omission, duplicate, false-claim, wrong-owner, wrong-branch, source-offset and malformed-source mutations rejected; nested branch/lambda/module scopes fail closed; nonliteral formulas remain checker/replay-owned")


if __name__ == "__main__":
    main()
