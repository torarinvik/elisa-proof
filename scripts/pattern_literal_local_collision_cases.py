"""Local-scrutinee collision programs kept separate to bound test source size."""

LOCAL_PATTERN_COLLISIONS = {
    # The source-type adapter authenticates direct formal parameters. Local scrutinees
    # must refuse facts instead of falling back to erased token text.
    'sview_local_01_vs_1_collision': '''
def sview_local_01_vs_1_collision() -> i64:
    ensure result > 0
    value: sview = "01"
    match value:
        "01":
            return 1
        "1":
            return 0
        _:
            return 1
''',
    'cstr_local_hex_vs_decimal_collision': '''
def cstr_local_hex_vs_decimal_collision() -> i64:
    ensure result > 0
    value: cstr = "0x1"
    match value:
        "0x1":
            return 1
        "1":
            return 0
        _:
            return 1
''',
    'u64_local_high_bit_literal_collision': '''
def u64_local_high_bit_literal_collision() -> i64:
    ensure result > 0
    value: u64 = 9223372036854775808u64
    match value:
        9223372036854775808u64:
            return 0
        _:
            return 1
''',
}
