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


ROOT = Path(__file__).resolve().parent.parent
BINARY = str(ROOT / "build/elisa-proof")
BASE = (ROOT / "examples/verified.elisa").read_bytes()
GOAL = "7"

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


def routes(directory, source, proof=None):
    """Every route, as (name, argument list ending in the source). `proof` is the rendered
    proof `--check-proof` reads; by default the one rendered from the control source."""
    return [
        ("text", [source]),
        ("json", ["--json", source]),
        ("theorems", ["--theorems", source]),
        ("goal", ["--goal", GOAL, source]),
        ("proof", ["--proof", GOAL, source]),
        ("check-proof", ["--check-proof", proof or directory / "control.proof", source]),
        ("suggest", ["--suggest", GOAL, source]),
        ("repair", ["--repair", GOAL, source]),
        ("repair-all", ["--repair-all", source]),
        ("tactics", ["--tactics", ROOT / "examples/tactic_script_target.json", source]),
        ("script", ["--script", directory / "control.script", source]),
    ]


def json_of(name, process):
    if name in ("text", "proof"):
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
    if name == "json":
        assert payload["status"] == "failed" and payload["verification_state"] != "proved", (variant, payload["status"])
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
    if name == "check-proof":
        assert payload["status"] in ("diverges", "not_found"), (variant, payload["status"])


def main():
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        control = directory / "control.elisa"
        control.write_bytes(BASE)
        (directory / "control.proof").write_bytes(run("--proof", GOAL, control).stdout)
        repair = json.loads(run("--repair", GOAL, control).stdout)
        (directory / "control.script").write_text(repair["script"])

        # Positive: a complete source passes every route, and a NUL inside a comment, which
        # both compilers skip, is not a defect.
        commented = directory / "comment_nul.elisa"
        commented.write_bytes(BASE + b"\n# a\x00b\n")
        for source in (control, commented):
            own = source.with_suffix(".proof")
            own.write_bytes(run("--proof", GOAL, source).stdout)
            for name, arguments in routes(directory, source, own):
                process = run(*arguments)
                assert process.returncode == 0, (source.name, name, process.stdout[:300])

        # Positive: an admissible source with an unrelated open goal still serves a goal-scoped
        # route. Inadmissibility, not incompleteness, is what the refusals below test.
        target = ROOT / "examples/tactic_repair_target.elisa"
        assert run("--tactics", ROOT / "examples/tactic_script_repair_target.json", target).returncode == 0
        assert run("--goal", "1", target).returncode == 0 and run("--theorems", target).returncode == 0
        partial = run("--repair-all", target)
        assert partial.returncode == 1 and json.loads(partial.stdout)["status"] in ("partial", "repaired")

        for variant, defect in MALFORMED.items():
            source = directory / (variant + ".elisa")
            source.write_bytes(BASE + defect)
            for name, arguments in routes(directory, source):
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
        for name, arguments in routes(directory, missing):
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
