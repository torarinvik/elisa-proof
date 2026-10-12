"""Reject pattern collisions between strings and fixed-width integer literals."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT/'build/elisa-proof'))

# Pattern ASTs erase source literal kinds, while the compiler lowers these patterns according to
# the scrutinee type. Each bad-return arm is reachable after compiler lowering and violates the
# postcondition. The u8 witnesses exercise well-typed upper-bound literal/range cases; the u64
# witness exercises the signed host-representation boundary.
PATTERN_COLLISIONS = {
    'sview_01_vs_1_collision': '''
def sview_01_vs_1_collision(value: sview) -> i64:
    ensure result > 0
    match value:
        "01":
            return 1
        "1":
            return 0
        _:
            return 1
''',
    'sview_1_vs_1_2_collision': '''
def sview_1_vs_1_2_collision(value: sview) -> i64:
    ensure result > 0
    match value:
        "1":
            return 1
        "1.2":
            return 0
        _:
            return 1
''',
    'sview_or_01_vs_1_collision': '''
def sview_or_01_vs_1_collision(value: sview) -> i64:
    ensure result > 0
    match value:
        "01" | "1":
            return 0
        _:
            return 1
''',
    'sview_true_spelling_collision': '''
def sview_true_spelling_collision(value: sview) -> i64:
    ensure result == 0
    match value:
        "true":
            return 1
        _:
            return 0
''',
    'sview_false_spelling_collision': '''
def sview_false_spelling_collision(value: sview) -> i64:
    ensure result == 0
    match value:
        "false":
            return 1
        _:
            return 0
''',
    'sview_null_spelling_collision': '''
def sview_null_spelling_collision(value: sview) -> i64:
    ensure result == 0
    match value:
        "null":
            return 1
        _:
            return 0
''',
    'cstr_or_boolean_spelling_collision': '''
def cstr_or_boolean_spelling_collision(value: cstr) -> i64:
    ensure result == 0
    match value:
        "true" | "false":
            return 1
        _:
            return 0
''',
    'u8_literal_boundary_collision': '''
def u8_literal_boundary_collision(value: u8) -> i64:
    ensure result > 0
    match value:
        255:
            return 0
        _:
            return 1
''',
    'u8_range_boundary_collision': '''
def u8_range_boundary_collision(value: u8) -> i64:
    ensure result > 0
    match value:
        254..=255:
            return 0
        _:
            return 1
''',
    'u64_high_bit_literal_collision': '''
def u64_high_bit_literal_collision(value: u64) -> i64:
    ensure result > 0
    match value:
        9223372036854775808u64:
            return 0
        _:
            return 1
''',
}

# A distinct identifier spelling is inside the checker/replay pair's deliberately narrow string
# literal subset. The branch assertion depends on the pattern fact, so blanket string-pattern
# refusal fails this positive control.
STRING_PATTERN_CONTROL = '''
def sview_identifier_pattern_control(value: sview) -> i64:
    ensure result == 0
    match value:
        "ready":
            assert value == "ready" by:
                assert value == "ready"
            return 0
        _:
            return 0
'''

CSTR_PATTERN_CONTROL = '''
def cstr_identifier_pattern_control(value: cstr) -> i64:
    ensure result == 0
    match value:
        "ready":
            assert value == "ready" by:
                assert value == "ready"
            return 0
        _:
            return 0
'''

GROUPED_STRING_PATTERN_CONTROL = '''
def sview_identifier_or_pattern_control(value: sview) -> i64:
    ensure result == 0
    match value:
        "ready" | "done":
            assert value == "ready" or value == "done" by:
                assert value == "ready" or value == "done"
            return 0
        _:
            return 0

def cstr_identifier_or_pattern_control(value: cstr) -> i64:
    ensure result == 0
    match value:
        "ready" | "done":
            assert value == "ready" or value == "done" by:
                assert value == "ready" or value == "done"
            return 0
        _:
            return 0
'''

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'pattern-collisions.elisa'
    path.write_text('\n'.join(PATTERN_COLLISIONS.values()))

    control_path = Path(folder) / 'string-pattern-control.elisa'
    control_path.write_text(STRING_PATTERN_CONTROL + '\n' + CSTR_PATTERN_CONTROL + '\n' + GROUPED_STRING_PATTERN_CONTROL)
    control = subprocess.run([BINARY, '--json', str(control_path)],
                             capture_output=True, text=True, timeout=120)
    control_report = json.loads(control.stdout)
    assert control.returncode == 0 and control_report['status'] == 'proved', control_report
    assert control_report['source']['admissible'] is True, control_report['source']
    assert control_report['summary']['semantic_errors'] == 0, control_report['semantic_diagnostics']
    assert control_report['replay']['gaps'] == 0, control_report['replay']
    assert control_report['replay']['certificates'] == control_report['replay']['replayed'], control_report['replay']
    assert not control_report['trust']['trusted_assumptions'], control_report['trust']
    for name in ('sview_identifier_pattern_control', 'cstr_identifier_pattern_control'):
        pattern_goals = [goal for goal in control_report['goals']
                         if goal['name'] == name
                         and goal['goal'].get('kind') == 'binary'
                         and goal['goal'].get('operator') == '=='
                         and goal['goal'].get('left', {}).get('kind') == 'ident'
                         and goal['goal'].get('left', {}).get('name') == 'value'
                         and goal['goal'].get('right') == {'kind': 'string', 'text': 'ready'}]
        assert len(pattern_goals) == 1 and pattern_goals[0]['proven'] \
            and pattern_goals[0]['replay_status'] == 'replayed', (name, pattern_goals, control_report['goals'])

        focused_control = subprocess.run([BINARY, '--function-json', name, str(control_path)],
                                         capture_output=True, text=True, timeout=120)
        focused_control_report = json.loads(focused_control.stdout)
        assert focused_control.returncode == 0 and focused_control_report['status'] == 'proved', (name, focused_control_report)
        assert any(row['name'] == name and row['proved']
                   for row in focused_control_report['functions']), (name, focused_control_report['functions'])

    for name in ('sview_identifier_or_pattern_control', 'cstr_identifier_or_pattern_control'):
        pattern_goals = [goal for goal in control_report['goals']
                         if goal['name'] == name and goal['proven']
                         and goal['replay_status'] == 'replayed']
        assert pattern_goals, (name, control_report['goals'])
        focused_control = subprocess.run([BINARY, '--function-json', name, str(control_path)],
                                         capture_output=True, text=True, timeout=120)
        focused_control_report = json.loads(focused_control.stdout)
        assert focused_control.returncode == 0 and focused_control_report['status'] == 'proved', (name, focused_control_report)
        assert any(row['name'] == name and row['proved']
                   for row in focused_control_report['functions']), (name, focused_control_report['functions'])

    run = subprocess.run([BINARY, '--json', str(path)],
                         capture_output=True, text=True, timeout=120)
    report = json.loads(run.stdout)
    assert run.returncode == 1 and report['status'] == 'failed', (
        run.returncode, report.get('status'), report.get('findings'))
    assert report['source']['admissible'] is True, report['source']
    assert report['summary']['semantic_errors'] == 0, report['semantic_diagnostics']
    assert report['replay']['gaps'] == 0, report['replay']
    assert report['replay']['certificates'] == report['replay']['replayed'], report['replay']
    assert not report['trust']['trusted_assumptions'], report['trust']
    for name in PATTERN_COLLISIONS:
        function = next((row for row in report['functions'] if row['name'] == name), None)
        assert function is not None and not function['proved'], (name, report['functions'])
        assert any(goal['name'] == name and not goal['proven'] for goal in report['goals']), (
            name, report['goals'])
        assert any(finding['name'] == name and finding['kind'] == 'ensure-unproven'
                   for finding in report['findings']), (name, report['findings'])

    for name in PATTERN_COLLISIONS:
        focused = subprocess.run([BINARY, '--function-json', name, str(path)],
                                 capture_output=True, text=True, timeout=120)
        focused_report = json.loads(focused.stdout)
        assert focused.returncode == 1 and focused_report['status'] == 'failed', (
            name, focused.returncode, focused_report.get('status'))
        assert focused_report['source']['admissible'] is True, (name, focused_report['source'])
        assert focused_report['summary']['semantic_errors'] == 0, (
            name, focused_report.get('semantic_diagnostics'))
        assert focused_report['replay']['gaps'] == 0, (name, focused_report['replay'])
        assert focused_report['replay']['certificates'] == focused_report['replay']['replayed'], (
            name, focused_report['replay'])
        assert not focused_report['trust']['trusted_assumptions'], (
            name, focused_report['trust'])
        declaration = next((row for row in focused_report['declaration_details']
                            if row.get('kind') == 'function' and row.get('name') == name), None)
        assert declaration is not None and not declaration['verified'], (
            name, focused_report['declaration_details'])
        assert any(goal['name'] == name and not goal['proven']
                   for goal in focused_report['goals']), (name, focused_report['goals'])

print('pattern literals: single and grouped identifier sview/cstr controls prove; ambiguous strings and fixed-width integer witnesses fail closed')
