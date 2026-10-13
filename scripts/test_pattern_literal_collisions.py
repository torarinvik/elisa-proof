"""Reject pattern facts that collide across distinct source literal spellings."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import tempfile
from qualified_test_binary import proof_test_binary
from pattern_literal_fixed_width_cases import FIXED_WIDTH_PATTERN_COLLISIONS
from pattern_literal_collision_report_checks import check_pattern_collision_reports

ROOT = Path(__file__).resolve().parents[1]
BINARY = proof_test_binary(ROOT)
PROCESS_TIMEOUT_SECONDS = 120
PROCESS_OUTPUT_LIMIT = 8 * 1024 * 1024


def run(command, label, timeout_seconds=PROCESS_TIMEOUT_SECONDS):
    """Bound each prover invocation so a bad child cannot hang or exhaust this gate."""
    stdout = bytearray()
    stderr = bytearray()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    deadline = time.monotonic() + timeout_seconds
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, stdout)
            selector.register(process.stderr, selectors.EVENT_READ, stderr)
            output_size = 0
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f'{label} timed out after {timeout_seconds}s')
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    output_size += len(chunk)
                    if output_size > PROCESS_OUTPUT_LIMIT:
                        raise AssertionError(
                            f'{label} output exceeded {PROCESS_OUTPUT_LIMIT} bytes')
                    key.data.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f'{label} timed out after {timeout_seconds}s')
        returncode = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(
            command, returncode, stdout.decode('utf-8', errors='replace'),
            stderr.decode('utf-8', errors='replace'),
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(f'{label} timed out after {timeout_seconds}s') from error
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout is not None and not process.stdout.closed:
            process.stdout.close()
        if process.stderr is not None and not process.stderr.closed:
            process.stderr.close()


def verify_process_limits():
    noisy = [sys.executable, '-c',
             f"import sys; sys.stdout.write('x' * {PROCESS_OUTPUT_LIMIT + 1}); sys.stdout.flush()"]
    try:
        run(noisy, 'output-cap self-test', timeout_seconds=10)
    except AssertionError as error:
        assert 'output exceeded' in str(error), error
    else:
        raise AssertionError('pattern test runner accepted output beyond its shared cap')

    slow = [sys.executable, '-c', 'import time; time.sleep(2)']
    try:
        run(slow, 'timeout self-test', timeout_seconds=0.05)
    except AssertionError as error:
        assert 'timed out' in str(error), error
    else:
        raise AssertionError('pattern test runner accepted a child beyond its deadline')


verify_process_limits()

# Pattern ASTs erase source literal kinds, while the compiler lowers these patterns according to
# the scrutinee type. Each bad-return arm is reachable after compiler lowering and violates the
# postcondition. The fixed-width witnesses cover signed and unsigned endpoints across widths,
# high-bit and range cases, and values beyond the signed host boundary.
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
    'cstr_01_vs_1_collision': '''
def cstr_01_vs_1_collision(value: cstr) -> i64:
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
    'sview_hex_string_vs_integer_collision': '''
def sview_hex_string_vs_integer_collision(value: sview) -> i64:
    ensure result > 0
    match value:
        "0x1":
            return 1
        "1":
            return 0
        _:
            return 1
''',
    'sview_exponent_string_vs_decimal_collision': '''
def sview_exponent_string_vs_decimal_collision(value: sview) -> i64:
    ensure result > 0
    match value:
        "1e0":
            return 1
        "1.0":
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
    'char_nul_vs_digit_zero_collision': '''
def char_nul_vs_digit_zero_collision(value: char) -> i64:
    ensure result > 0
    match value:
        '\\0':
            return 1
        '0':
            return 0
        _:
            return 1
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
    'u8_high_bit_literal_collision': '''
def u8_high_bit_literal_collision(value: u8) -> i64:
    ensure result > 0
    match value:
        128:
            return 0
        _:
            return 1
''',
    'u16_high_bit_literal_collision': '''
def u16_high_bit_literal_collision(value: u16) -> i64:
    ensure result > 0
    match value:
        32768:
            return 0
        _:
            return 1
''',
    'u32_high_bit_literal_collision': '''
def u32_high_bit_literal_collision(value: u32) -> i64:
    ensure result > 0
    match value:
        2147483648:
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
    'i8_signed_lower_boundary_collision': '''
def i8_signed_lower_boundary_collision(value: i8) -> i64:
    ensure result > 0
    match value:
        -128:
            return 0
        _:
            return 1
''',
    'i8_signed_upper_boundary_collision': '''
def i8_signed_upper_boundary_collision(value: i8) -> i64:
    ensure result > 0
    match value:
        127:
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
    'u64_max_literal_collision': '''
def u64_max_literal_collision(value: u64) -> i64:
    ensure result > 0
    match value:
        18446744073709551615u64:
            return 0
        _:
            return 1
''',
}
PATTERN_COLLISIONS.update(FIXED_WIDTH_PATTERN_COLLISIONS)

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

PUNCTUATED_STRING_PATTERN_CONTROLS = '''
def sview_punctuated_string_pattern_control(value: sview) -> i64:
    ensure result == 0
    match value:
        "ready-now?":
            assert value == "ready-now?" by:
                assert value == "ready-now?"
            return 0
        _:
            return 0

def cstr_punctuated_string_pattern_control(value: cstr) -> i64:
    ensure result == 0
    match value:
        "ready.now/2":
            assert value == "ready.now/2" by:
                assert value == "ready.now/2"
            return 0
        _:
            return 0
'''

EMPTY_STRING_PATTERN_CONTROLS = '''
def sview_empty_string_pattern_control(value: sview) -> i64:
    ensure result == 0
    match value:
        "":
            assert value == "" by:
                assert value == ""
            return 0
        _:
            return 0

def cstr_empty_string_pattern_control(value: cstr) -> i64:
    ensure result == 0
    match value:
        "":
            assert value == "" by:
                assert value == ""
            return 0
        _:
            return 0
'''

CHAR_PATTERN_CONTROL = '''
def char_pattern_identifier_control(value: char) -> i64:
    ensure result == 0
    match value:
        'A':
            assert value == 'A' by:
                assert value == 'A'
            return 0
        _:
            return 0

def char_pattern_digit_control(value: char) -> i64:
    ensure result == 0
    match value:
        '0':
            assert value == '0' by:
                assert value == '0'
            return 0
        _:
            return 0

def char_pattern_newline_control(value: char) -> i64:
    ensure result == 0
    match value:
        '\\n':
            assert value == '\\n' by:
                assert value == '\\n'
            return 0
        _:
            return 0

def char_pattern_null_control(value: char) -> i64:
    ensure result == 0
    match value:
        '\\0':
            assert value == '\\0' by:
                assert value == '\\0'
            return 0
        _:
            return 0
'''

# The theorem catalog contains lemmas, not ordinary function summaries. Keep one collision
# witness in that declaration class so the public theorem-output route cannot pass vacuously.
THEOREM_PATTERN_COLLISION_NAME = 'theorem_sview_01_vs_1_collision'
THEOREM_PATTERN_COLLISION = '''
lemma theorem_sview_01_vs_1_collision(value: sview):
    match value:
        "01":
            pass
        "1":
            assert false by:
                pass
'''

THEOREM_FIXED_WIDTH_PATTERN_COLLISION_NAME = 'theorem_u64_high_bit_pattern_collision'
THEOREM_FIXED_WIDTH_PATTERN_COLLISION = '''
lemma theorem_u64_high_bit_pattern_collision(value: u64):
    match value:
        9223372036854775808u64:
            assert false by:
                pass
'''

# Generic binders can reuse lowercase names such as `sview`. The spelling alone must not
# authenticate the runtime representation used by a string-pattern fact.
GENERIC_BUILTIN_TYPE_NAME_SHADOW = '''
def generic_sview_type_parameter[sview](value: sview) -> i64:
    ensure result == 0
    match value:
        "ready":
            assert value == "ready" by:
                assert value == "ready"
            return 0
        _:
            return 0

def generic_cstr_type_parameter[cstr](value: cstr) -> i64:
    ensure result == 0
    match value:
        "ready":
            assert value == "ready" by:
                assert value == "ready"
            return 0
        _:
            return 0

def generic_char_type_parameter[char](value: char) -> i64:
    ensure result == 0
    match value:
        'A':
            assert value == 'A' by:
                assert value == 'A'
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
    path.write_text('\n'.join(PATTERN_COLLISIONS.values()) + '\n' + THEOREM_PATTERN_COLLISION + '\n' + THEOREM_FIXED_WIDTH_PATTERN_COLLISION)

    control_path = Path(folder) / 'string-pattern-control.elisa'
    control_path.write_text(STRING_PATTERN_CONTROL + '\n' + CSTR_PATTERN_CONTROL + '\n' + PUNCTUATED_STRING_PATTERN_CONTROLS + '\n' + EMPTY_STRING_PATTERN_CONTROLS + '\n' + CHAR_PATTERN_CONTROL + '\n' + GROUPED_STRING_PATTERN_CONTROL)
    control = run([BINARY, '--json', str(control_path)], 'pattern positive controls')
    control_report = json.loads(control.stdout)
    assert control.returncode == 0 and control_report['status'] == 'proved', control_report
    assert control_report['source']['admissible'] is True, control_report['source']
    assert control_report['summary']['semantic_errors'] == 0, control_report['semantic_diagnostics']
    assert control_report['replay']['gaps'] == 0, control_report['replay']
    assert control_report['replay']['certificates'] == control_report['replay']['replayed'], control_report['replay']
    assert not control_report['trust']['trusted_assumptions'], control_report['trust']
    expected_string_controls = {
        'sview_identifier_pattern_control': 'ready',
        'cstr_identifier_pattern_control': 'ready',
        'sview_punctuated_string_pattern_control': 'ready-now?',
        'cstr_punctuated_string_pattern_control': 'ready.now/2',
        'sview_empty_string_pattern_control': '',
        'cstr_empty_string_pattern_control': '',
    }
    for name, expected_text in expected_string_controls.items():
        pattern_goals = [goal for goal in control_report['goals']
                         if goal['name'] == name
                         and goal['goal'].get('kind') == 'binary'
                         and goal['goal'].get('operator') == '=='
                         and goal['goal'].get('left', {}).get('kind') == 'ident'
                         and goal['goal'].get('left', {}).get('name') == 'value'
                         and goal['goal'].get('right') == {'kind': 'string', 'text': expected_text}]
        assert len(pattern_goals) == 1 and pattern_goals[0]['proven'] \
            and pattern_goals[0]['replay_status'] == 'replayed', (name, pattern_goals, control_report['goals'])

        focused_control = run([BINARY, '--function-json', name, str(control_path)],
                              f'focused pattern positive control {name}')
        focused_control_report = json.loads(focused_control.stdout)
        assert focused_control.returncode == 0 and focused_control_report['status'] == 'proved', (name, focused_control_report)
        assert any(row['name'] == name and row['proved']
                   for row in focused_control_report['functions']), (name, focused_control_report['functions'])

    for name in ('char_pattern_identifier_control', 'char_pattern_digit_control',
                 'char_pattern_newline_control', 'char_pattern_null_control'):
        pattern_goals = [goal for goal in control_report['goals']
                         if goal['name'] == name
                         and goal['goal'].get('kind') == 'binary'
                         and goal['goal'].get('operator') == '=='
                         and goal['goal'].get('left', {}).get('kind') == 'ident'
                         and goal['goal'].get('left', {}).get('name') == 'value'
                         and goal['goal'].get('right', {}).get('kind') == 'char']
        assert (len(pattern_goals) == 1 and pattern_goals[0]['proven']
                and pattern_goals[0]['replay_status'] == 'replayed'), (
                    name, pattern_goals, control_report['goals'])

        focused_control = run([BINARY, '--function-json', name, str(control_path)],
                              f'focused character pattern positive control {name}')
        focused_control_report = json.loads(focused_control.stdout)
        assert focused_control.returncode == 0 and focused_control_report['status'] == 'proved', (name, focused_control_report)
        assert any(row['name'] == name and row['proved']
                   for row in focused_control_report['functions']), (name, focused_control_report['functions'])

    for name in ('sview_identifier_or_pattern_control', 'cstr_identifier_or_pattern_control'):
        pattern_goals = [goal for goal in control_report['goals']
                         if goal['name'] == name and goal['proven']
                         and goal['replay_status'] == 'replayed']
        assert pattern_goals, (name, control_report['goals'])
        focused_control = run([BINARY, '--function-json', name, str(control_path)],
                              f'focused grouped pattern positive control {name}')
        focused_control_report = json.loads(focused_control.stdout)
        assert focused_control.returncode == 0 and focused_control_report['status'] == 'proved', (name, focused_control_report)
        assert any(row['name'] == name and row['proved']
                   for row in focused_control_report['functions']), (name, focused_control_report['functions'])

    generic_path = Path(folder) / 'generic-type-name-shadow.elisa'
    generic_path.write_text(GENERIC_BUILTIN_TYPE_NAME_SHADOW)
    for name in ('generic_sview_type_parameter', 'generic_cstr_type_parameter', 'generic_char_type_parameter'):
        generic_run = run([BINARY, '--function-json', name, str(generic_path)],
                          f'generic builtin-name pattern shadow {name}')
        generic_report = json.loads(generic_run.stdout)
        assert generic_run.returncode != 0 and generic_report['status'] != 'proved', generic_report
        assert generic_report['source']['admissible'] is True, generic_report['source']
        assert generic_report['summary']['semantic_errors'] == 0, generic_report['semantic_diagnostics']
        assert generic_report['replay']['gaps'] == 0, generic_report['replay']
        assert generic_report['replay']['certificates'] == generic_report['replay']['replayed'], generic_report['replay']
        assert not generic_report['trust']['trusted_assumptions'], generic_report['trust']
        generic_pattern_goals = [goal for goal in generic_report['goals']
                                 if goal['goal'].get('kind') == 'binary'
                                 and goal['goal'].get('operator') == '=='
                                 and goal['goal'].get('left', {}).get('kind') == 'ident'
                                 and goal['goal'].get('left', {}).get('name') == 'value'
                                 and ((name == 'generic_char_type_parameter' and goal['goal'].get('right', {}).get('kind') == 'char')
                                      or (name != 'generic_char_type_parameter' and goal['goal'].get('right') == {'kind': 'string', 'text': 'ready'}))]
        assert len(generic_pattern_goals) == 1 and not generic_pattern_goals[0]['proven'], (
            name, generic_pattern_goals, generic_report['goals'])

    check_pattern_collision_reports(run, BINARY, path, PATTERN_COLLISIONS,
                                    (THEOREM_PATTERN_COLLISION_NAME,
                                     THEOREM_FIXED_WIDTH_PATTERN_COLLISION_NAME))

print('pattern literals: string and char controls prove; string, char-code, and fixed-width collisions fail closed')
