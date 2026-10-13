"""Additional fixed-width endpoint witnesses for pattern-collision regressions."""

FIXED_WIDTH_PATTERN_COLLISIONS = {
    'u16_upper_boundary_collision': '''
def u16_upper_boundary_collision(value: u16) -> i64:
    ensure result > 0
    match value:
        65535u16:
            return 0
        _:
            return 1
''',
    'u32_upper_boundary_collision': '''
def u32_upper_boundary_collision(value: u32) -> i64:
    ensure result > 0
    match value:
        4294967295u32:
            return 0
        _:
            return 1
''',
    'u32_range_boundary_collision': '''
def u32_range_boundary_collision(value: u32) -> i64:
    ensure result > 0
    match value:
        4294967294u32..=4294967295u32:
            return 0
        _:
            return 1
''',
    'i16_signed_lower_boundary_collision': '''
def i16_signed_lower_boundary_collision(value: i16) -> i64:
    ensure result > 0
    match value:
        -32768i16:
            return 0
        _:
            return 1
''',
    'i16_signed_upper_boundary_collision': '''
def i16_signed_upper_boundary_collision(value: i16) -> i64:
    ensure result > 0
    match value:
        32767i16:
            return 0
        _:
            return 1
''',
    'i32_signed_lower_boundary_collision': '''
def i32_signed_lower_boundary_collision(value: i32) -> i64:
    ensure result > 0
    match value:
        -2147483648i32:
            return 0
        _:
            return 1
''',
    'i32_signed_upper_boundary_collision': '''
def i32_signed_upper_boundary_collision(value: i32) -> i64:
    ensure result > 0
    match value:
        2147483647i32:
            return 0
        _:
            return 1
''',
    'i64_signed_lower_boundary_collision': '''
def i64_signed_lower_boundary_collision(value: i64) -> i64:
    ensure result > 0
    match value:
        -9223372036854775808i64:
            return 0
        _:
            return 1
''',
    'i64_signed_upper_boundary_collision': '''
def i64_signed_upper_boundary_collision(value: i64) -> i64:
    ensure result > 0
    match value:
        9223372036854775807i64:
            return 0
        _:
            return 1
''',
}
