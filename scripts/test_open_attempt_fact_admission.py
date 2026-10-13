"""Source-bound tactics admit only the parser-checked facts on an open attempt."""
import json
from pathlib import Path
import subprocess
import tempfile
from qualified_test_binary import proof_test_binary


ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)
SOURCE_TEXT = """def open_local_binding(value: u8) -> void:
    requires value < 255
    saved: u8 = value + 1
    assert saved + 1 == 4 by:
        assert saved + 1 == 4
"""


def run(*arguments):
    return subprocess.run([str(BINARY), *map(str, arguments)], capture_output=True,
                          text=True, timeout=120)


with tempfile.TemporaryDirectory(prefix="elisa-open-attempt-facts-") as temporary:
    directory = Path(temporary)
    source = directory / "open_local_binding.elisa"
    source.write_text(SOURCE_TEXT, encoding="utf-8")

    checked = run("--json", source)
    report = json.loads(checked.stdout)
    assert checked.returncode == 1, (checked.returncode, checked.stderr, report)
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    targets = [goal for goal in report["goals"]
               if goal["name"] == "open_local_binding" and goal["rule"] == "goal"]
    assert len(targets) == 1 and not targets[0]["proven"], targets
    target = targets[0]
    assert target["fact_origins_complete"], target
    assert any(origin is not None and origin["kind"] == "local-binding"
               for origin in target["fact_origins"]), target

    focused = run("--goal", str(target["goal_id"]), source)
    focused_report = json.loads(focused.stdout)
    assert focused.returncode == 1 and focused_report["goal_fingerprint"] is not None, focused_report
    script = directory / "source-facts.json"
    script.write_text(json.dumps({
        "format": "elisa-proof-tactics-v1",
        "target": {
            "goal_id": target["goal_id"],
            "goal_fingerprint": focused_report["goal_fingerprint"]["value"],
        },
        "actions": [{"action": "assumption", "accepted": False}],
    }), encoding="utf-8")

    attempted = run("--tactics", script, source)
    tactic_report = json.loads(attempted.stdout)
    assert attempted.returncode == 1, (attempted.returncode, attempted.stderr, tactic_report)
    binding = tactic_report["source_goal_binding"]
    assert binding["bound"] and binding["goal_id"] == target["goal_id"], binding
    assert binding["fingerprint_match"] is True, binding
    assert tactic_report["source"]["admissible"] is True, tactic_report["source"]
    assert tactic_report["tactic"]["valid"] is True, tactic_report["tactic"]
    assert tactic_report["tactic"]["solved"] is False, tactic_report["tactic"]
    assert tactic_report["tactic"]["trace_replayed"] is True, tactic_report["tactic"]
    assert tactic_report["tactic"]["kernel_trace_replayed"] is True, tactic_report["tactic"]
    assert tactic_report["state"]["initial_facts"] == target["facts"]
    assert tactic_report["state"]["initial_goal"] == target["goal"]
    assert tactic_report["state"]["trace"][0]["accepted"] is False

    forged_script = directory / "forged-initial-state.json"
    forged_script.write_text(json.dumps({
        "format": "elisa-proof-tactics-v1",
        "target": {
            "goal_id": target["goal_id"],
            "goal_fingerprint": focused_report["goal_fingerprint"]["value"],
        },
        # Portable initial states are never authoritative for a source-bound attempt.
        "initial": {"facts": [target["goal"]], "goal": target["goal"]},
        "actions": [{"action": "assumption", "accepted": True}],
    }), encoding="utf-8")
    forged = run("--tactics", forged_script, source)
    forged_report = json.loads(forged.stdout)
    assert forged.returncode == 1, (forged.returncode, forged.stderr, forged_report)
    assert forged_report["source_goal_binding"]["bound"] is True, forged_report
    assert forged_report["source_goal_binding"]["fingerprint_match"] is True, forged_report
    assert forged_report["tactic"]["valid"] is False, forged_report["tactic"]
    assert forged_report["tactic"]["solved"] is False, forged_report["tactic"]

print("open-attempt facts: source local binding retained; forged portable initial state refused")
