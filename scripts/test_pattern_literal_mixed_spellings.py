"""Verify source admission and replay for quoted and bare string-pattern spellings."""

import json
from pathlib import Path
import tempfile

from pattern_literal_process_runner import run, verify_process_limits
from qualified_test_binary import proof_test_binary


ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)
verify_process_limits()

# Pattern ASTs erase lexer token kinds; string scrutinees interpret both spellings as text.
MIXED_QUOTED_BARE_STRING_PATTERN_CONTROLS = '''
def sview_quoted_and_bare_digit_pattern_control(value: sview) -> i64:
    ensure result == 0
    match value:
        "1":
            assert value == "1" by:
                assert value == "1"
            return 0
        1:
            assert value == "1" by:
                assert value == "1"
            return 0
        _:
            return 0

def cstr_quoted_and_bare_digit_pattern_control(value: cstr) -> i64:
    ensure result == 0
    match value:
        "1":
            assert value == "1" by:
                assert value == "1"
            return 0
        1:
            assert value == "1" by:
                assert value == "1"
            return 0
        _:
            return 0
'''

with tempfile.TemporaryDirectory() as folder:
    source_path = Path(folder) / "mixed-string-patterns.elisa"
    source_path.write_text(MIXED_QUOTED_BARE_STRING_PATTERN_CONTROLS, encoding="utf-8")
    result = run([BINARY, "--json", str(source_path)], "mixed quoted/bare string patterns")
    report = json.loads(result.stdout)
    assert result.returncode == 0 and report["status"] == "proved", report
    assert report["source"]["admissible"] is True, report["source"]

    for name in (
        "sview_quoted_and_bare_digit_pattern_control",
        "cstr_quoted_and_bare_digit_pattern_control",
    ):
        goals = [
            goal for goal in report["goals"]
            if goal["name"] == name
            and goal["goal"].get("kind") == "binary"
            and goal["goal"].get("operator") == "=="
            and goal["goal"].get("left", {}).get("name") == "value"
            and goal["goal"].get("right") == {"kind": "string", "text": "1"}
        ]
        assert len(goals) == 2 and all(
            goal["proven"] and goal["replay_status"] == "replayed" for goal in goals
        ), (name, goals)
        focused = run(
            [BINARY, "--function-json", name, str(source_path)],
            f"focused mixed quoted/bare string pattern control {name}",
        )
        focused_report = json.loads(focused.stdout)
        assert focused.returncode == 0 and focused_report["status"] == "proved", focused_report
        assert focused_report["replay"]["gaps"] == 0, focused_report["replay"]
        assert any(row["name"] == name and row["proved"] for row in focused_report["functions"])
