"""G68: a bare constant in an included module resolves in that module, not to a same-named constant of the including module, in both kernel proposition typing and fact import."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(fixture, expected_status):
    run = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / fixture)],
        capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == expected_status, (fixture, run.returncode, run.stderr)
    return json.loads(run.stdout)


positive = report("include_constant_scope_probe.elisa", 0)
assert positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["trust"]["trusted_assumptions"] == [], positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in positive["goals"]), positive
assert {goal["name"] for goal in positive["goals"]} >= {"within", "narrow", "go", "keep_floor"}, positive

rejected = report("rejected_include_constant_scope.elisa", 1)
assert rejected["status"] == "failed", rejected
assert rejected["summary"]["semantic_errors"] == 0, rejected
assert rejected["replay"]["gaps"] == 0, rejected
kinds = {(finding["name"], finding["kind"]) for finding in rejected["findings"]}
assert kinds == {("too_wide", "ensure-unproven"), ("too_tight", "ensure-unproven")}, rejected
assert not any(finding["kind"] == "contract-proposition-type" for finding in rejected["findings"]), rejected
claimed = {goal["name"] for goal in rejected["goals"] if goal["proven"] and goal["rule"] == "goal"}
assert not ({"too_wide", "too_tight"} & claimed), rejected

print("include constant scope: each module's bare constant types and resolves in its own module; wrong-bound controls refused")
