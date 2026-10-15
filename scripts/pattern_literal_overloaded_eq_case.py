"""Adversarial source where match lowering must respect overloaded equality."""

STRING_EQ_OVERRIDE_PRELUDE = '''
protocol Eq:
    def __eq__(self: Self, other: Self) -> bool

protocol Less:
    def __lt__(self: Self, other: Self) -> bool

# Exercise the compiler's current cross-protocol dunder dispatch: an impl may contain
# an operator-named member even when its declared protocol is unrelated.
impl Less for sview:
    def __lt__(self: sview, other: sview) -> bool:
        return false

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

impl Eq for i8:
    def __eq__(self: i8, other: i8) -> bool:
        return false

impl Eq for u8:
    def __eq__(self: u8, other: u8) -> bool:
        return false

impl Eq for char:
    def __eq__(self: char, other: char) -> bool:
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
    'i8_pattern_overloaded_eq_collision': '''
def i8_pattern_overloaded_eq_collision(value: i8) -> bool:
    ensure result == true
    match value:
        7:
            return value == 7
        _:
            return true
''',
    'u8_pattern_overloaded_eq_collision': '''
def u8_pattern_overloaded_eq_collision(value: u8) -> bool:
    ensure result == true
    match value:
        7:
            return value == 7
        _:
            return true
''',
    'char_pattern_overloaded_eq_collision': '''
def char_pattern_overloaded_eq_collision(value: char) -> bool:
    ensure result == true
    match value:
        'a':
            return value == 'a'
        _:
            return true
''',
}
