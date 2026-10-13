#!/usr/bin/env python3
"""Run every CLI route against every class of malformed source.

Exit status 0 is the verdict a caller can act on without reading the output, so no route may
return it for a source that failed to parse, import, type-check, or form its propositions. Each
malformed variant keeps a goal the kernel proves on its own (goal 7 of verified.elisa), so a
route that looked only at that goal would admit it.
"""
import json
from pathlib import Path
import subprocess
import tempfile
from qualified_test_binary import proof_test_binary


ROOT = Path(__file__).resolve().parent.parent
BINARY = proof_test_binary(ROOT)
BASE = (ROOT / "examples/verified.elisa").read_bytes()
GOAL = "7"
FUNCTION = "successor"

# Each defect is appended after the base, so goal ids 0..7 stay those of verified.elisa.
MALFORMED = {
    "parse": b"\ndef broken(:\n    return\n",
    "import": b'\ninclude "./missing_file.elisa"\n',
    "semantic": b"\ndef unresolved_name() -> i64:\n    return missing_value\n",
    "proposition": b"\ndef rejected_nonboolean_ensure(values: darray[i64]&) -> i64:\n    ensure values[0]\n    return 0\n",
    # The stage1 lexer passes over a NUL in code; the reference compiler does not.
    "nul-identifier": b"\ndef nul_\x00name() -> i64:\n    return 0\n",
    "nul-string": b'\ndef nul_text() -> sview:\n    return "a#\x00b"\n',
}


def run(*arguments):
    return subprocess.run([BINARY, *map(str, arguments)], capture_output=True, timeout=120)


def routes(directory, source, proof=None, package=None, hints=None):
    """Every route, as (name, argument list ending in the source). `proof` is the rendered
    proof `--check-proof` reads. Correspondence receives a replayable control package and
    linear-hints receives a valid empty hint stream; callers use a package generated from the
    exact positive source, or the control package for malformed-source refusal cases."""
    package = package or directory / "control.package.json"
    hints = hints or directory / "control.hints"
    return [
        ("text", [source]),
        ("json", ["--json", source]),
        ("summary-json", ["--summary-json", source]),
        ("function-json", ["--function-json", FUNCTION, source]),
        ("theorems", ["--theorems", source]),
        ("goal", ["--goal", GOAL, source]),
        ("proof", ["--proof", GOAL, source]),
        ("check-proof", ["--check-proof", proof or directory / "control.proof", source]),
        ("suggest", ["--suggest", GOAL, source]),
        ("explain", ["--explain", GOAL, source]),
        ("repair", ["--repair", GOAL, source]),
        ("repair-all", ["--repair-all", source]),
        ("linear-hints", ["--linear-hints", hints, source]),
        ("tactics", ["--tactics", ROOT / "examples/tactic_script_target.json", source]),
        ("script", ["--script", directory / "control.script", source]),
        ("package", ["--package", source]),
        ("correspondence", ["--correspondence", package, source]),
    ]


def json_of(name, process):
    if name in ("text", "proof", "explain"):
        return None
    if name == "correspondence" and not process.stdout.lstrip().startswith(b"{"):
        # A source/import read failure can be reported before the JSON correspondence
        # checker is entered. It is still a nonzero, fail-closed route result.
        return None
    return json.loads(process.stdout)


def check_refused(variant, name, process):
    assert process.returncode != 0, (variant, name, process.stdout[:300])
    payload = json_of(name, process)
    if payload is None:
        return
    source = payload.get("source")
    if isinstance(source, dict) and "admissible" in source:
        assert source["admissible"] is False, (variant, name, source)
    if name in ("json", "summary-json", "function-json", "linear-hints"):
        assert payload["status"] == "failed" and payload["verification_state"] != "proved", (variant, payload["status"])
    if name == "function-json":
        function_rows = [row for row in payload.get("functions", []) if row.get("name") == FUNCTION]
        assert len(function_rows) == 1 and function_rows[0]["proved"] is False, (variant, function_rows)
    if name == "theorems":
        assert payload["theorems"] == [], (variant, payload["theorems"])
    if name == "suggest":
        assert payload["candidates"] == [], (variant, payload["candidates"])
    if name == "repair":
        assert payload["status"] in ("inadmissible", "not_found") and payload["script"] is None, (variant, payload)
        assert payload["search"]["tried"] == 0, (variant, payload["search"])
    if name == "repair-all":
        assert payload["status"] == "inadmissible", (variant, payload["status"])
        assert all(goal["status"] == "unrepaired" and goal["script"] is None for goal in payload["goals"]), variant
    if name in ("tactics", "script"):
        assert payload["status"] == "failed", (variant, name, payload["status"])
    if name == "package":
        # An inadmissible source exports no theorem for the portable checker to replay.
        assert payload["theorems"] == [] and payload["kernel"]["nodes"] == [], (variant, len(payload["theorems"]))
    if name == "check-proof":
        assert payload["status"] in ("diverges", "not_found"), (variant, payload["status"])
    if name == "explain":
        assert b"proven, replayed certificate" not in process.stdout, (variant, process.stdout[:500])
    if name == "correspondence" and payload is not None:
        assert payload["source_admissible"] is False, (variant, payload)


def main():
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        control = directory / "control.elisa"
        control.write_bytes(BASE)
        (directory / "control.proof").write_bytes(run("--proof", GOAL, control).stdout)
        repair = json.loads(run("--repair", GOAL, control).stdout)
        (directory / "control.script").write_text(repair["script"])
        (directory / "control.hints").write_text("# valid empty hint stream\n", encoding="utf-8")
        control_package = run("--package", control)
        assert control_package.returncode == 0, control_package.stdout[:500]
        (directory / "control.package.json").write_bytes(control_package.stdout)

        # Positive: a complete source passes every route, and a NUL inside a comment, which
        # both compilers skip, is not a defect.
        commented = directory / "comment_nul.elisa"
        commented.write_bytes(BASE + b"\n# a\x00b\n")
        for source in (control, commented):
            own = source.with_suffix(".proof")
            own.write_bytes(run("--proof", GOAL, source).stdout)
            package = source.with_suffix(".package.json")
            packaged = run("--package", source)
            assert packaged.returncode == 0, (source.name, packaged.stdout[:500])
            package.write_bytes(packaged.stdout)
            for name, arguments in routes(directory, source, own, package):
                process = run(*arguments)
                assert process.returncode == 0, (source.name, name, process.stdout[:300])
                if name == "correspondence":
                    assert json.loads(process.stdout)["source_admissible"] is True, process.stdout[:500]

        # An admissible source with an unrelated open obligation remains incomplete. A replayed
        # certificate is visible as evidence, but source completeness is required to publish proof.
        target = ROOT / "examples/tactic_repair_target.elisa"
        # A parser-bound compound ensure remains an admissible tactic target even while a
        # separate result-dependent obligation keeps whole-source completeness false.
        assert run("--tactics", ROOT / "examples/tactic_script_repair_target.json", target).returncode == 0
        incomplete = directory / "admissible_open.elisa"
        incomplete.write_bytes(BASE + b"\ndef independent_open(x: i64) -> i64:\n"
                               b"    requires x == 2\n    ensure result == x + 1\n    return x\n")
        overview = json.loads(run("--json", incomplete).stdout)
        assert overview["summary"]["semantic_errors"] == 0 and overview["summary"]["unproven"] > 0, overview
        scoped = run("--goal", GOAL, incomplete)
        scoped_report = json.loads(scoped.stdout)
        assert scoped.returncode == 1 and scoped_report["status"] == "unknown", scoped_report
        assert scoped_report["goal"]["proven"] is False and scoped_report["goal"]["replay_status"] == "replayed", scoped_report
        assert scoped_report["source"]["admissible"] is True and scoped_report["source"]["complete"] is False, scoped_report
        admitted = run("--theorems", incomplete)
        assert admitted.returncode == 0 and json.loads(admitted.stdout)["theorems"] == [], admitted.stdout
        partial = run("--repair-all", target)
        assert partial.returncode == 1 and json.loads(partial.stdout)["status"] in ("partial", "repaired")

        # Repair is goal-scoped: a result-dependent ensure remains outside exact AST admission,
        # while a compound assert-by goal is bound to its exact parser proposition. The ensure
        # must not be searched or offered as a runnable script, while the admitted goal remains
        # eligible for bounded search.
        repair_admission = directory / "repair_goal_admission.elisa"
        repair_admission.write_text(
            "def repair_goal_admission(x: i64, y: i64) -> i64:\n"
            "    requires x == 2\n"
            "    ensure result == y\n"
            "    assert (y == 3 and x == 2) by:\n"
            "        pass\n"
            "    return x\n",
            encoding="utf-8",
        )
        repair_admission_overview = json.loads(run("--json", repair_admission).stdout)
        assert repair_admission_overview["source"]["admissible"] is True, repair_admission_overview["source"]
        assert repair_admission_overview["source"]["goal_admissions_complete"] is True, repair_admission_overview["source"]
        unsupported_repair_goal = next(
            goal for goal in repair_admission_overview["goals"]
            if goal["name"] == "repair_goal_admission" and goal["line"] == 3
        )
        assert unsupported_repair_goal["proven"] is False, unsupported_repair_goal
        assert_by_repair_goal = next(
            goal for goal in repair_admission_overview["goals"]
            if goal["name"] == "repair_goal_admission" and goal["line"] == 4
        )
        assert assert_by_repair_goal["proven"] is False, assert_by_repair_goal

        focused_repair = run("--repair", str(unsupported_repair_goal["goal_id"]), repair_admission)
        focused_repair_report = json.loads(focused_repair.stdout)
        assert focused_repair.returncode != 0 and focused_repair_report["status"] == "source-unbound", focused_repair_report
        assert focused_repair_report["search"]["tried"] == 0 and focused_repair_report["script"] is None, focused_repair_report

        repair_batch = run("--repair-all", repair_admission)
        repair_batch_report = json.loads(repair_batch.stdout)
        assert repair_batch.returncode == 1 and repair_batch_report["source"]["admissible"] is True, repair_batch_report
        skipped = next(goal for goal in repair_batch_report["goals"]
                       if goal["goal_id"] == unsupported_repair_goal["goal_id"])
        assert skipped["source_admission"] == "source-unbound" and skipped["status"] == "source-unbound", skipped
        assert skipped["tried"] == 0 and skipped["script"] is None, skipped
        eligible = next(goal for goal in repair_batch_report["goals"]
                        if goal["goal_id"] == assert_by_repair_goal["goal_id"])
        assert eligible["source_admission"] == "admitted" and eligible["tried"] > 0, eligible

        # The kernel can replay reflexivity after substituting a return expression. The
        # source checker may refuse the parametric postcondition, but no presentation route
        # may turn a source-unbound or incomplete admission into a proof.
        replay_identity = directory / "replay_identity.elisa"
        replay_identity.write_text(
            "def replay_identity(x: i64) -> i64:\n"
            "    requires x >= 0\n"
            "    ensure result == x\n"
            "    return x\n",
            encoding="utf-8",
        )
        identity_run = run("--json", replay_identity)
        identity_report = json.loads(identity_run.stdout)
        assert identity_report["summary"]["semantic_errors"] == 0, identity_report["semantic_diagnostics"]
        identity_goals = [goal for goal in identity_report["goals"] if goal["name"] == "replay_identity"]
        assert identity_goals and all(goal["replay_status"] == "replayed" for goal in identity_goals), identity_report["goals"]
        assert identity_report["source"]["goal_admissions_complete"] is True, identity_report["source"]
        assert identity_report["source"]["admissible"] is False, identity_report["source"]
        assert identity_run.returncode != 0 and identity_report["status"] != "proved", identity_report
        assert all(not goal["proven"] and goal.get("refusal_gate") == "source-unbound"
                   for goal in identity_goals), identity_goals
        identity_declaration = next(row for row in identity_report["declaration_details"]
                                    if row.get("kind") == "function" and row.get("name") == "replay_identity")
        assert identity_declaration["verified"] is False, identity_declaration
        identity_goal_ids = {goal["goal_id"] for goal in identity_goals}
        assert identity_goal_ids.intersection(goal["goal_id"] for goal in identity_report["repair_queue"]), identity_report["repair_queue"]

        package_run = run("--package", replay_identity)
        identity_package = json.loads(package_run.stdout)
        assert package_run.returncode != 0, identity_package
        assert identity_package["source"]["admissible"] is False, identity_package["source"]
        assert not identity_package["theorems"] and not identity_package["kernel"]["nodes"], identity_package

        summary_run = run("--summary-json", replay_identity)
        identity_summary = json.loads(summary_run.stdout)
        assert summary_run.returncode != 0 and identity_summary["status"] != "proved", identity_summary
        summary_counts = identity_summary["summary"]
        assert summary_counts["proven"] is None or summary_counts["proven"] < summary_counts["obligations"], summary_counts

        identity_goal_id = str(identity_goals[0]["goal_id"])
        # The same source-bound status must survive the smaller CLI projections. The default
        # report, focused goal JSON, and proof-text export must not turn a replayed but
        # unauthenticated certificate into a proof.
        text_identity = run(replay_identity)
        text_identity_output = text_identity.stdout.decode("utf-8", errors="replace")
        assert text_identity.returncode != 0, text_identity_output
        assert "verification state: unknown" in text_identity_output, text_identity_output
        assert "proven: 0" in text_identity_output, text_identity_output

        focused_identity = run("--goal", identity_goal_id, replay_identity)
        focused_identity_report = json.loads(focused_identity.stdout)
        assert focused_identity.returncode != 0 and focused_identity_report["status"] != "proved", focused_identity_report
        assert focused_identity_report["source"]["admissible"] is False, focused_identity_report
        assert focused_identity_report["goal_admissible"] is False, focused_identity_report
        assert focused_identity_report["goal"]["proven"] is False, focused_identity_report
        assert focused_identity_report["goal"]["replay_status"] == "replayed", focused_identity_report

        proof_identity = run("--proof", identity_goal_id, replay_identity)
        proof_identity_output = proof_identity.stdout.decode("utf-8", errors="replace")
        assert proof_identity.returncode != 0, proof_identity_output
        assert "goal_admissible=false" in proof_identity_output, proof_identity_output
        assert "selected goal was not fully admitted as proved" in proof_identity_output, proof_identity_output
        assert f"\nproof replay_identity_{identity_goal_id}:" not in proof_identity_output, proof_identity_output

        # Theorem/lemma catalog has its own source-admission projection. The result-free
        # postcondition and body assertion both match their parser ASTs and replay by
        # reflexivity, so the theorem-level claim should remain admitted. `result == x` above
        # stays the negative control for transformed postconditions.
        lemma_source = directory / "replay_identity_lemma.elisa"
        lemma_source.write_text(
            "lemma replay_identity_lemma(x: i64):\n"
            "    ensure x == x\n"
            "    assert x == x\n",
            encoding="utf-8",
        )
        theorem_run = run("--theorems", lemma_source)
        theorem_catalog = json.loads(theorem_run.stdout)
        assert theorem_run.returncode == 0, theorem_catalog
        assert theorem_catalog["source"]["admissible"] is True, theorem_catalog["source"]
        assert theorem_catalog["source"]["goal_admissions_complete"] is True, theorem_catalog["source"]
        lemma_row = next(row for row in theorem_catalog["theorems"] if row["name"] == "replay_identity_lemma")
        assert lemma_row["proof_replay_complete"] and lemma_row["kernel_verified"], lemma_row
        assert lemma_row["verified"] is True and lemma_row["source_claim_admissible"] is True, lemma_row
        assert lemma_row["verification_reason"] != "source-unbound", lemma_row
        lemma_overview_run = run("--json", lemma_source)
        lemma_overview = json.loads(lemma_overview_run.stdout)
        ensure_goal = next(goal for goal in lemma_overview["goals"]
                           if goal["name"] == "replay_identity_lemma" and goal["line"] == 2)
        assert ensure_goal["replay_status"] == "replayed" and ensure_goal["proven"], ensure_goal
        assert ensure_goal.get("refusal_gate") != "source-unbound", ensure_goal
        assert_goal = next(goal for goal in lemma_overview["goals"]
                           if goal["name"] == "replay_identity_lemma" and goal["line"] == 3)
        assert assert_goal["replay_status"] == "replayed" and assert_goal["proven"], assert_goal
        catalog_ensure_goal = next(goal for goal in lemma_row["proof_goals"]
                                  if goal["goal_id"] == ensure_goal["goal_id"])
        assert catalog_ensure_goal["replayed"] and catalog_ensure_goal["proven"], catalog_ensure_goal
        assert catalog_ensure_goal["source_admission"] == "admitted", catalog_ensure_goal
        catalog_assert_goal = next(goal for goal in lemma_row["proof_goals"]
                                   if goal["goal_id"] == assert_goal["goal_id"])
        assert catalog_assert_goal["replayed"] and catalog_assert_goal["proven"], catalog_assert_goal
        assert catalog_assert_goal["source_admission"] == "admitted", catalog_assert_goal
        assert all(goal["proven"] == (goal["source_admission"] == "admitted")
                   for goal in lemma_row["proof_goals"]), lemma_row

        explanation = run("--explain", identity_goal_id, replay_identity)
        explanation_text = explanation.stdout.decode("utf-8", errors="replace")
        assert explanation.returncode != 0, explanation_text
        assert "proven, replayed certificate" not in explanation_text, explanation_text

        # A different source claim can make the whole file inadmissible while an earlier
        # goal remains locally matched and replayed. Per-goal renderings may report that local
        # evidence, but no CLI route may return success for the globally inadmissible source.
        mixed_admission = directory / "local_goal_global_source_failure.elisa"
        mixed_admission.write_bytes(
            BASE + b"\ndef mixed_source_unbound(x: i64) -> i64:\n"
            b"    requires x >= 0\n    ensure result == x\n    return x\n"
        )
        mixed_goal = run("--goal", GOAL, mixed_admission)
        mixed_goal_report = json.loads(mixed_goal.stdout)
        assert mixed_goal.returncode == 1 and mixed_goal_report["source"]["admissible"] is False, mixed_goal_report
        assert mixed_goal_report["goal_admissible"] is True, mixed_goal_report
        assert mixed_goal_report["goal"]["proven"] is True and mixed_goal_report["goal"]["replay_status"] == "replayed", mixed_goal_report

        mixed_proof = run("--proof", GOAL, mixed_admission)
        mixed_proof_text = mixed_proof.stdout.decode("utf-8", errors="replace")
        assert mixed_proof.returncode == 1 and "admissible=false" in mixed_proof_text, mixed_proof_text
        assert "goal_admissible=true" in mixed_proof_text, mixed_proof_text
        mixed_proof_path = directory / "mixed_source.proof"
        mixed_proof_path.write_bytes(mixed_proof.stdout)
        mixed_check = run("--check-proof", mixed_proof_path, mixed_admission)
        mixed_check_report = json.loads(mixed_check.stdout)
        assert mixed_check.returncode == 1 and mixed_check_report["status"] == "matches", mixed_check_report
        assert mixed_check_report["admissible"] is False and mixed_check_report["goal_admissible"] is True, mixed_check_report

        mixed_explanation = run("--explain", GOAL, mixed_admission)
        assert mixed_explanation.returncode == 1, mixed_explanation.stdout.decode("utf-8", errors="replace")

        for variant, defect in MALFORMED.items():
            source = directory / (variant + ".elisa")
            source.write_bytes(BASE + defect)
            for name, arguments in routes(directory, source, package=directory / "control.package.json"):
                check_refused(variant, name, run(*arguments))
            # A proof rendered from the malformed source itself matches it line for line; the
            # match must still not certify the source.
            rendered = run("--proof", GOAL, source)
            if rendered.returncode != 2:
                own = directory / (variant + ".proof")
                own.write_bytes(rendered.stdout)
                checked = run("--check-proof", own, source)
                payload = json.loads(checked.stdout)
                assert checked.returncode == 1 and payload["status"] == "matches" and payload["admissible"] is False, variant

        # Malformed input to the route itself: a missing source, and a script bound to other
        # source bytes. A comment changes the fingerprint and nothing else.
        missing = directory / "missing.elisa"
        for name, arguments in routes(directory, missing, package=directory / "control.package.json"):
            process = run(*arguments)
            assert process.returncode == 2 and b"could not read source" in process.stdout, (name, process.stdout[:200])
        edited = directory / "edited.elisa"
        edited.write_bytes(BASE + b"\n# edited\n")
        fingerprint = json.loads(run("--json", control).stdout)["source"]["fingerprint"]["value"]
        bound = json.loads((ROOT / "examples/tactic_script_target.json").read_text())
        bound["source_fingerprint"] = fingerprint
        bound_path = directory / "bound.json"
        bound_path.write_text(json.dumps(bound))
        assert run("--tactics", bound_path, control).returncode == 0
        stale = run("--tactics", bound_path, edited)
        assert stale.returncode == 1 and json.loads(stale.stdout)["source"]["fingerprint_match"] is False
        diverged = run("--check-proof", directory / "control.proof", edited)
        assert diverged.returncode == 1 and json.loads(diverged.stdout)["status"] == "diverges"

        # Budget: exhausting a search is an open goal, never a proved or repaired one.
        budget = ROOT / "examples/rejected_budget.elisa"
        assert run("--json", budget).returncode == 1
        batch = run("--repair-all", budget)
        assert batch.returncode == 1 and json.loads(batch.stdout)["status"] != "repaired"
    print(f"source admission matrix: {len(MALFORMED)} malformed classes refused on all {len(routes(Path('.'), 'x'))} routes")


if __name__ == "__main__":
    main()
