"""Coverage for typed aggregate field reads and bounded-container non-transfer controls."""
import json
import os
from pathlib import Path
import subprocess


if not __debug__:
    raise SystemExit("resource projection coverage must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(example, expected_exit, expected_status):
    result = subprocess.run(
        [str(BINARY), "--json", str(ROOT / "examples" / (example + ".elisa"))],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == expected_exit, (example, result.returncode, result.stderr)
    parsed = json.loads(result.stdout)
    assert parsed["status"] == expected_status, (example, parsed.get("status"), parsed.get("summary"))
    assert parsed["replay"]["certificates"] == parsed["replay"]["replayed"], (example, parsed["replay"])
    assert parsed["replay"]["gaps"] == 0, (example, parsed["replay"])
    return parsed


positive = report("resource_projection_e144_typed_copy", 0, "proved")
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert positive["summary"]["obligations"] > 0, positive["summary"]
assert positive["summary"]["proven"] == positive["summary"]["obligations"], positive["summary"]
assert positive["trust"]["trusted_assumptions"] == [], positive["trust"]
assert positive["summary"]["unproven"] == 0, positive["summary"]
assert any(
    goal["name"] == "resource_projection_e144_typed_copy"
    and goal["rule"] == "resource-safety" and goal["proven"]
    and goal.get("replay_status") == "replayed"
    for goal in positive["goals"]
), "typed aggregate copy resource-safety certificate did not replay"

mutable_write = report("rejected_resource_projection_e144_mutable_field_write", 1, "failed")
assert any(
    finding["name"] == "rejected_resource_projection_e144_mutable_field_write"
    and finding["kind"] in {"resource-write-readonly", "borrow-readonly-write"}
    for finding in mutable_write["findings"]
), "write through immutable aggregate container was not refused by resource analysis"

for example in (
    "rejected_resource_projection_e144_shadow",
    "rejected_resource_projection_e144_cross_container",
):
    negative = report(example, 1, "failed")
    assert any(
        goal["name"] == example and goal["rule"] == "resource-safety"
        and goal["proven"] and goal.get("replay_status") == "replayed"
        for goal in negative["goals"]
    ), (example, "resource-safety certificate must replay even while the bounds negative is refused")
    assert any(
        goal["name"] == example and goal["rule"] == "index-upper" and not goal["proven"]
        for goal in negative["goals"]
    ), (example, "expected the shadowed/different container index-upper obligation to remain unproven")

print("e144 resource projection coverage: typed copy replays; mutable write, shadow, and cross-container controls refuse")
