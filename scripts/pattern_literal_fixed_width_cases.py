"""Additional fixed-width endpoint witnesses for pattern-collision regressions."""

FIXED_WIDTH_PATTERN_COLLISIONS = {
    'u8_high_bit_range_collision': '''
def u8_high_bit_range_collision(value: u8) -> i64:
    ensure result > 0
    match value:
        127u8..=128u8:
            return 0
        _:
            return 1
''',
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
    'u32_high_bit_range_collision': '''
def u32_high_bit_range_collision(value: u32) -> i64:
    ensure result > 0
    match value:
        2147483647u32..=2147483648u32:
            return 0
        _:
            return 1
''',
    'u16_high_bit_range_collision': '''
def u16_high_bit_range_collision(value: u16) -> i64:
    ensure result > 0
    match value:
        32767u16..=32768u16:
            return 0
        _:
            return 1
''',
    'u64_high_bit_range_collision': '''
def u64_high_bit_range_collision(value: u64) -> i64:
    ensure result > 0
    match value:
        9223372036854775807u64..=9223372036854775808u64:
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
    'i8_signed_negative_range_collision': '''
def i8_signed_negative_range_collision(value: i8) -> i64:
    ensure result > 0
    match value:
        -128i8..=-127i8:
            return 0
        _:
            return 1
''',
    'i16_signed_zero_crossing_range_collision': '''
def i16_signed_zero_crossing_range_collision(value: i16) -> i64:
    ensure result > 0
    match value:
        -1i16..=1i16:
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
    'i64_signed_negative_range_collision': '''
def i64_signed_negative_range_collision(value: i64) -> i64:
    ensure result > 0
    match value:
        -9223372036854775808i64..=-9223372036854775807i64:
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


# Positive counterparts ensure collision rejection still preserves endpoint matching.
_FIXED_WIDTH_RANGE_ENDPOINTS = (
    ("u8", "u8", "127u8", "128u8"),
    ("u16", "u16", "32767u16", "32768u16"),
    ("u32", "u32", "2147483647u32", "2147483648u32"),
    ("u64", "u64", "9223372036854775807u64", "9223372036854775808u64"),
    ("i8", "i8", "-128i8", "-127i8"),
    ("i16", "i16", "-32768i16", "-32767i16"),
    ("i32", "i32", "-2147483648i32", "-2147483647i32"),
    ("i64", "i64", "-9223372036854775808i64", "-9223372036854775807i64"),
)


def _fixed_width_range_control(name, type_name, endpoint, lower, upper):
    return f'''\ndef {name}(value: {type_name}) -> i64:
    requires value == {endpoint}
    ensure result == 1
    match value:
        {lower}..={upper}:
            return 1
        _:
            return 0
'''


FIXED_WIDTH_RANGE_CONTROLS = {}
for _type_name, _type, _lower, _upper in _FIXED_WIDTH_RANGE_ENDPOINTS:
    FIXED_WIDTH_RANGE_CONTROLS[f"{_type_name}_range_lower_endpoint_control"] = (
        _fixed_width_range_control(
            f"{_type_name}_range_lower_endpoint_control", _type, _lower, _lower, _upper
        )
    )
    FIXED_WIDTH_RANGE_CONTROLS[f"{_type_name}_range_upper_endpoint_control"] = (
        _fixed_width_range_control(
            f"{_type_name}_range_upper_endpoint_control", _type, _upper, _lower, _upper
        )
    )
