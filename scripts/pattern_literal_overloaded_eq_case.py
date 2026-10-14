"""Adversarial source where match bytes differ from overloaded string equality."""

STRING_EQ_OVERRIDE_PRELUDE = '''
protocol Eq:
    def __eq__(self: Self, other: Self) -> bool

impl Eq for sview:
    def __eq__(self: sview, other: sview) -> bool:
        return false

impl Eq for cstr:
    def __eq__(self: cstr, other: cstr) -> bool:
        return false

impl Eq for i64:
    def __eq__(self: i64, other: i64) -> bool:
        return false

impl Eq for u64:
    def __eq__(self: u64, other: u64) -> bool:
        return false
'''

STRING_EQ_OVERRIDE_COLLISIONS = {
    'sview_pattern_overloaded_eq_collision': '''
def sview_pattern_overloaded_eq_collision(value: sview) -> bool:
    ensure result == true
    match value:
        "needle":
            return value == "needle"
        _:
            return true
''',
    'cstr_pattern_overloaded_eq_collision': '''
def cstr_pattern_overloaded_eq_collision(value: cstr) -> bool:
    ensure result == true
    match value:
        "needle":
            return value == "needle"
        _:
            return true
''',
    'i64_pattern_overloaded_eq_collision': '''
def i64_pattern_overloaded_eq_collision(value: i64) -> bool:
    ensure result == true
    match value:
        7:
            return value == 7
        _:
            return true
''',
    'u64_pattern_overloaded_eq_collision': '''
def u64_pattern_overloaded_eq_collision(value: u64) -> bool:
    ensure result == true
    match value:
        7:
            return value == 7
        _:
            return true
''',
}
