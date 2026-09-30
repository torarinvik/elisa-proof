"""Scoped literal constants distinguish branch statuses and returned action codes."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(source: str, expected_exit: int) -> dict:
    run = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / source)],
        capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == expected_exit, (source, run.returncode, run.stderr, run.stdout)
    return json.loads(run.stdout)


positive = report("qualified_constant_pins.elisa", 0)
assert positive["status"] == positive["verification_state"] == "proved", positive
assert positive["summary"]["semantic_errors"] == positive["summary"]["semantic_diagnostics"] == 0, positive
assert positive["summary"]["obligations"] == positive["summary"]["proven"] > 0, positive
assert positive["findings"] == [], positive
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] == positive["summary"]["proven"], positive
assert positive["replay"]["gaps"] == 0 and positive["trust"]["trusted_assumptions"] == [], positive
target = next(item for item in positive["declaration_details"] if item.get("name") == "timer_due_effect")
assert target["verified"] and target["ensures"] == 6, target

negative = report("rejected_qualified_constant_pin.elisa", 1)
assert negative["status"] == "failed" and negative["verification_state"] == "disproved", negative
assert negative["summary"]["semantic_errors"] == 0, negative
assert negative["replay"]["gaps"] == 0, negative
assert negative["replay"]["certificates"] == negative["replay"]["replayed"], negative
assert any(finding["kind"] == "ensure-unproven" and finding["name"] == "wrong_timeout_effect"
           and finding["status"] == "disproved" and finding["counterexample_found"]
           for finding in negative["findings"]), negative

print("qualified literal constants: timer-effect partition replays and false action mapping is refuted")
