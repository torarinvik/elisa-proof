"""G68: a bare call inside an included module resolves to that module's own function, and a qualified `Mod::f` (also nested `Geometry::Scalar::f`) only within Mod, never to a same-named function of the including module, in both the prover and kernel replay."""
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


positive = report("include_function_scope_probe.elisa", 0)
assert positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive
assert positive["trust"]["trusted_assumptions"] == [], positive
assert positive["replay"]["gaps"] == 0, positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0, positive
assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in positive["goals"]), positive
assert {goal["name"] for goal in positive["goals"]} >= {"bump", "lift", "twice", "via_inner", "via_nested"}, positive

rejected = report("rejected_include_function_scope.elisa", 1)
assert rejected["status"] == "failed", rejected
assert rejected["summary"]["semantic_errors"] == 0, rejected
assert rejected["replay"]["gaps"] == 0, rejected
kinds = {(finding["name"], finding["kind"]) for finding in rejected["findings"]}
assert kinds == {("wrong_bare", "ensure-unproven"), ("wrong_qualified", "ensure-unproven"), ("wrong_nested", "ensure-unproven")}, rejected

print("include function scope: bare and qualified calls resolve in their own module; wrong-capture controls refused")
