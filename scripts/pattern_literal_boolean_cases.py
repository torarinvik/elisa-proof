"""Boolean pattern literals that must not become trusted proof facts."""

BOOLEAN_PATTERN_COLLISIONS = {
    'bool_true_pattern_collision': '''
def bool_true_pattern_collision(value: bool) -> i64:
    ensure result > 0
    match value:
        true:
            return 0
        false:
            return 1
''',
    'bool_false_pattern_collision': '''
def bool_false_pattern_collision(value: bool) -> i64:
    ensure result > 0
    match value:
        false:
            return 0
        true:
            return 1
''',
}
