"""Pin source contracts for the active Python/ElisaScript port."""

import ast
import csv
import hashlib
import re
from pathlib import Path
from test_elisascript_report_output_reader_contract import check_python_reader_contract


ROOT = Path(__file__).resolve().parents[1]
python_reference = ROOT / "scripts/test_report_output_loop_layout.py"
elisa_counterpart = ROOT / "scripts/test_report_output_loop_layout.elisascript"
interpreter = ROOT.parent / "elisa-script/src/ir/interpret.elisa"
lowerer = ROOT.parent / "elisa-script/src/ir/lower_ast.elisa"
ir_model = ROOT.parent / "elisa-script/src/ir/ir_model.elisa"
verifier = ROOT.parent / "elisa-script/src/ir/ir_verify.elisa"
execution_facade = ROOT.parent / "elisa-script/src/ir/execution.elisa"
launcher_source = ROOT.parent / "elisa-script/src/driver/elisascript.elisa"
builtin_registry = ROOT.parent / "elisa-script/vendor/elisa-compiler/src/semantic/builtin_registry.elisa"
assert python_reference.parent == elisa_counterpart.parent
assert python_reference.stem == elisa_counterpart.stem
python_source = python_reference.read_text(encoding="utf-8")
elisa_source = elisa_counterpart.read_text(encoding="utf-8")

with (ROOT / "scripts/elisascript/PORTING_INVENTORY.csv").open(newline="", encoding="utf-8") as inventory_file:
    active_rows = [row for row in csv.DictReader(inventory_file) if row["python_path"] == "scripts/test_report_output_loop_layout.py"]
assert len(active_rows) == 1, active_rows
active_row = active_rows[0]
assert active_row["elisascript_path"] == "scripts/test_report_output_loop_layout.elisascript" and active_row["status"] == "active_unqualified" and active_row["python_sha256"] == hashlib.sha256(python_reference.read_bytes()).hexdigest(), active_row
interpreter_source = interpreter.read_text(encoding="utf-8")
lowerer_source = lowerer.read_text(encoding="utf-8")
ir_model_source = ir_model.read_text(encoding="utf-8")
verifier_source = verifier.read_text(encoding="utf-8")
registry_source = builtin_registry.read_text(encoding="utf-8")
bounded_reader = (ROOT.parent / "elisa-script/src/runtime/bounded_text_posix.elisa").read_text(encoding="utf-8")
reader_body = bounded_reader.split("def read_utf8[T: Str](", 1)[1].split("def descriptor_shape", 1)[0]
runtime_strings = (ROOT.parent / "elisa-script/vendor/elisa-compiler/elisacore_std/elisacore_runtime_strings.elisa").read_text(encoding="utf-8")
runtime_prelude = (ROOT.parent / "elisa-script/vendor/elisa-compiler/elisacore_std/elisacore_runtime_prelude.elisa").read_text(encoding="utf-8")


def python_assignment(name: str):
    tree = ast.parse(python_source)
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in statement.targets
        ):
            return ast.literal_eval(statement.value)
    raise AssertionError(f"Python assignment {name} not found")


def quote_elisa_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


python_fragments = python_assignment("required")
array_match = re.search(r"required:\s*darray\[sview\]\s*=\s*\[(.*?)\n\s*\]", elisa_source, re.S)
assert array_match, "ElisaScript required fragment list is missing"
elisa_fragments = tuple(
    ast.literal_eval(line.strip().removesuffix(","))
    for line in array_match.group(1).splitlines()
    if line.strip()
)
assert python_fragments == elisa_fragments, (python_fragments, elisa_fragments)

# Both scripts derive the same repository root and read the same target file.
assert "Path(__file__).resolve().parents[1]" in python_source
for path_step in (
    "path_real(Script::invocation_path())",
    "script_file.parent()",
    "proof_root: Path = script_directory.parent()",
    'proof_root.joinpath("src/app/report_output_serialization_helpers.elisa")',
):
    assert path_step in elisa_source, path_step

# Pin the bounded-reader builtin and the runtime implementation it reaches.
assert "PROOF_REPORT_OUTPUT_LOOP_LAYOUT_MAX_SOURCE_BYTES: usize = 16777216" in elisa_source
assert 'include "../runtime/bounded_text_posix.elisa"' in execution_facade.read_text(encoding="utf-8")
assert 'include "../ir/execution.elisa"' in launcher_source.read_text(encoding="utf-8")
assert "include \"../../elisa-script/src/runtime/bounded_text_posix.elisa\"" not in elisa_source
assert "using EsBoundedText" not in elisa_source
assert "read_text_bounded(source_file, PROOF_REPORT_OUTPUT_LOOP_LAYOUT_MAX_SOURCE_BYTES)" in elisa_source
assert "source_file.read_text()" not in elisa_source
assert 'name: "read_text_bounded", receiver: "global", arity_min: 2, arity_max: 2, argument_types: "Path,usize", return_type: "sview", effects: "File.Read", errors: "FileIoError", opcode: "ReadBoundedText"' in registry_source
main_signature = next(line for line in elisa_source.splitlines() if line.startswith("def main("))
assert "File.Read" in main_signature and "Global" not in main_signature, main_signature
assert "EsBoundedText::read_utf8_path_text(path_value.text, maximum_bytes)" in interpreter_source
assert "EsBoundedText::read_utf8(path(path_value.text), maximum_bytes)" not in interpreter_source
assert "def read_utf8[T: Str](input_path: T, maximum_bytes: usize)" in bounded_reader
assert 'return try read_utf8_text(f"{input_path}", maximum_bytes)' in bounded_reader
assert "def read_utf8_path_text(input_path: sview, maximum_bytes: usize)" in bounded_reader
path_text_reader = bounded_reader.split("def read_utf8_path_text(", 1)[1].split("def read_utf8_text(", 1)[0]
assert "input_path: sview, maximum_bytes: usize" in path_text_reader
assert "return try read_utf8_text(input_path, maximum_bytes)" in path_text_reader
assert "def read_utf8_text(input_path: sview" in bounded_reader
for reader_signature in (
    "def read_utf8[T: Str](input_path: T, maximum_bytes: usize)",
    "def read_utf8_path_text(input_path: sview, maximum_bytes: usize)",
    "def read_utf8_text(input_path: sview, maximum_bytes: usize)",
):
    signature = next(line for line in bounded_reader.splitlines() if line.strip().startswith(reader_signature))
    assert "Global{Read,Write}" in signature, signature
string_copy = runtime_strings.split("def string_view_copy(view: sview) -> cstr:", 1)[1].split("# ------------------------------------------------------------", 1)[0]
assert "can Memory.Allocate, Abort.Panic, Global{Read,Write}:" in string_copy
assert "intern_small_string(view.data, view.len.usize())" in string_copy
assert "alloc_perm(allocation_i64)" in string_copy
assert "register_perm_string_len(out.cast[u8&], length)" in string_copy
assert "global mutable small_string_cache" in runtime_prelude
assert "global mutable string_len_cache" in runtime_prelude
assert "can Global:\n                contents: sview = try EsBoundedText::read_utf8_path_text(path_value.text, maximum_bytes)" in interpreter_source
assert "EsRuntime::DarwinStatMode::MASK" in bounded_reader
assert "EsRuntime::DarwinOpenFlags::RDONLY" in bounded_reader
assert "EsProcessExecSearch::DarwinErrno::EINTR" in bounded_reader
assert "return sview(owned_text, 0, len(contents).i64())" in bounded_reader
assert "Opcode.ReadBoundedText" in interpreter_source
assert 'callee_name == "read_text_bounded"' in lowerer_source
assert "ReadBoundedText" in ir_model_source and "Opcode.ReadBoundedText" in verifier_source
bounded_read_dispatch = interpreter_source.split("def evaluate_read_bounded_text(", 1)[1].split("\n\n", 1)[0]
assert "path_value.kind != RuntimeValueKind.Text or maximum_value.kind != RuntimeValueKind.Int" in bounded_read_dispatch
assert "maximum_value.integer < 0" in bounded_read_dispatch
assert "maximum_bytes.i64() != maximum_value.integer" in bounded_read_dispatch
assert "interpret_set_failure(machine, InterpretFailure.FileIo)" in bounded_read_dispatch
assert "MAX_BYTES: usize = 16777216" in bounded_reader
assert "PATH_BYTES: usize = 4096" in bounded_reader
assert "READ_CHUNK_BYTES: usize = 16384" in bounded_reader
assert python_assignment("READ_CHUNK_BYTES") == 16384
assert "READ_CALLS_PER_CHUNK" not in bounded_reader
assert "read_call_limit" not in bounded_reader
check_python_reader_contract(python_source)
assert "READ_CALLS_PER_CHUNK" not in python_source
assert "read_call_limit" not in python_source
assert 'raise ReadError.InvalidPath if input_path == "" or len(input_path) >= Limits::PATH_BYTES or sview_contains_byte(input_path, 0)' in bounded_reader
assert "READ_EINTR_RETRIES: usize = 4" in bounded_reader
assert "DarwinOpenFlags::NONBLOCK" in bounded_reader and "DarwinOpenFlags::CLOSE_ON_EXEC" in bounded_reader
assert "text_is_valid_utf8(contents)" in bounded_reader
assert "same_file(named_before_open, opened)" in reader_body
assert "if opened.size != named_before_open.size" in reader_body
assert "same_file(opened, named_after_open)" in reader_body
assert "stable_file(opened, final_opened)" in reader_body
assert "stable_file(final_opened, final_named)" in reader_body
assert (
    "        def same_file(left: ElisascriptStat, right: ElisascriptStat) -> bool:\n"
    "            return left.device == right.device and left.inode == right.inode"
) in bounded_reader
assert (
    "        def stable_file(left: ElisascriptStat, right: ElisascriptStat) -> bool:\n"
    "            return same_file(left, right) and left.size == right.size and left.modify_time.seconds == right.modify_time.seconds and left.modify_time.nanoseconds == right.modify_time.nanoseconds and left.change_time.seconds == right.change_time.seconds and left.change_time.nanoseconds == right.change_time.nanoseconds"
) in bounded_reader
assert reader_body.index("if opened.size > maximum_bytes.i64():") < reader_body.index("named_after_open: mutable ElisascriptStat")
read_loop = reader_body.split("remaining: usize = maximum_bytes - bytes.count", 1)[1].split("\n\n            final_opened:", 1)[0]
assert "read_call_limit" not in read_loop and "read_calls" not in read_loop
for read_contract in (
    "probe_capacity: usize = remaining + 1\n                capacity: usize = probe_capacity if probe_capacity < chunk.count else chunk.count",
    "amount: isize = elisascript_posix_read(descriptor, chunk_pointer.cast[mutable void&], capacity)",
    "if errno[0] == EsProcessExecSearch::DarwinErrno::EINTR and interrupted < Limits::READ_EINTR_RETRIES:\n                        interrupted <- interrupted + 1\n                        continue",
    "if read_count > capacity:\n                    try close_descriptor(descriptor)\n                    raise ReadError.ReadFailed",
    "if read_count > remaining:\n                    try close_descriptor(descriptor)\n                    raise ReadError.LimitExceeded",
    "if bytes.count > initial_size or read_count > initial_size - bytes.count:\n                    try close_descriptor(descriptor)\n                    raise ReadError.Changed",
    "for offset in 0..<read_count |bytes, chunk|:\n                    bytes.push(chunk[offset])",
    "if capacity < Limits::READ_CHUNK_BYTES:\n                    current_opened: mutable ElisascriptStat = zeroed\n                    if not fstat_descriptor(descriptor, current_opened):\n                        try close_descriptor(descriptor)\n                        raise ReadError.ReadFailed\n                    if not stable_file(opened, current_opened):\n                        try close_descriptor(descriptor)\n                        raise ReadError.Changed",
    "interrupted <- 0",
):
    assert read_contract in read_loop, read_contract
owned_reader = reader_body.split("descriptor: int = open_path(path_pointer)", 1)[1].split(
    "contents: sview = bytes_view(bytes)", 1
)[0]
owned_reader_lines = [line for line in owned_reader.splitlines() if line.strip()]
for index, line in enumerate(owned_reader_lines):
    if "try close_descriptor(descriptor)" in line:
        assert index + 1 < len(owned_reader_lines)
        assert "raise ReadError." in owned_reader_lines[index + 1], line
    if "raise ReadError." in line and "if descriptor < 0" not in line:
        assert index > 0 and "try close_descriptor(descriptor)" in owned_reader_lines[index - 1], line
for helper_name in ("open_path", "stat_path", "fstat_descriptor"):
    helper_body = bounded_reader.split(f"def {helper_name}(", 1)[1].split("\n\n", 1)[0]
    assert "errno[0] == EsProcessExecSearch::DarwinErrno::EINTR" in helper_body, helper_name
    assert "retries < Limits::READ_EINTR_RETRIES" in helper_body, helper_name
assert "errno[0] == EsProcessExecSearch::DarwinErrno::EINTR and interrupted < Limits::READ_EINTR_RETRIES" in reader_body
stable_read_position = reader_body.index("stable: bool =")
owned_contents_position = reader_body.index("contents: sview = bytes_view(bytes)")
direct_close_position = reader_body.find("close_status: int = elisascript_posix_close(descriptor)")
direct_close_error = (
    direct_close_position >= 0
    and stable_read_position < direct_close_position < owned_contents_position
    and "close_status: int = elisascript_posix_close(descriptor)" in reader_body
    and "raise ReadError.ReadFailed if close_status != 0" in reader_body
    and direct_close_position < reader_body.index("raise ReadError.ReadFailed if close_status != 0")
)
final_helper_close_position = reader_body.rfind("try close_descriptor(descriptor)")
close_helper_error = (
    "def close_descriptor(descriptor: int) -> void error[ReadError]" in bounded_reader
    and "raise ReadError.ReadFailed if elisascript_posix_close(descriptor) != 0" in bounded_reader
    and stable_read_position < final_helper_close_position < owned_contents_position
)
assert direct_close_error or close_helper_error
assert 'source.replace("\\r\\n", "\\n").replace("\\r", "\\n")' in elisa_source
assert "proof_report_output_loop_layout_contains(normalized_source, fragment)" in elisa_source
assert "failure[index] <- prefix_length" in elisa_source
assert "matched <- failure[matched - 1]" in elisa_source
assert "failure: mutable usize[256] = zeroed" in elisa_source
assert "PROOF_REPORT_OUTPUT_LOOP_LAYOUT_MAX_FRAGMENT_BYTES: usize = 256" in elisa_source
assert max(len(fragment.encode("utf-8")) for fragment in python_fragments) <= 256
assert "normalized_source.contains(fragment)" not in elisa_source
matcher_start = elisa_source.index("def proof_report_output_loop_layout_contains(")
matcher_end = elisa_source.index("\ndef main(", matcher_start)
matcher_source = elisa_source[matcher_start:matcher_end].rstrip()
expected_matcher_source = '''def proof_report_output_loop_layout_contains(haystack: sview, needle: sview) -> bool:
    haystack_length: usize = sview_len(haystack)
    needle_length: usize = sview_len(needle)
    return true if needle_length == 0
    return false if needle_length > haystack_length
    return false if needle_length > PROOF_REPORT_OUTPUT_LOOP_LAYOUT_MAX_FRAGMENT_BYTES
    failure: mutable usize[256] = zeroed
    prefix_length: mutable usize = 0
    for index in 1..<needle_length |failure, needle, prefix_length|:
        while prefix_length > 0 and sview_at(needle, index) != sview_at(needle, prefix_length) |failure, needle, index, prefix_length|:
            prefix_length <- failure[prefix_length - 1]
        prefix_length <- prefix_length + 1 if sview_at(needle, index) == sview_at(needle, prefix_length)
        failure[index] <- prefix_length
    matched: mutable usize = 0
    for index in 0..<haystack_length |haystack, needle, failure, matched|:
        while matched > 0 and sview_at(haystack, index) != sview_at(needle, matched) |haystack, needle, failure, index, matched|:
            matched <- failure[matched - 1]
        matched <- matched + 1 if sview_at(haystack, index) == sview_at(needle, matched)
        return true if matched == needle_length
    return false'''
assert matcher_source == expected_matcher_source

bounded_text_docs = (ROOT.parent / "elisa-script/docs/semantics.md").read_text(encoding="utf-8")
assert "read_text_bounded" in bounded_text_docs
assert "Positive short reads continue until EOF" in bounded_text_docs
assert "Total POSIX read attempts are also capped" not in bounded_text_docs

tree = ast.parse(python_source)


def python_function(name: str):
    matches = [
        statement
        for statement in tree.body
        if isinstance(statement, ast.FunctionDef) and statement.name == name
    ]
    assert len(matches) == 1, name
    return matches[0]


assert ast.unparse(python_function("same_file")) == '''def same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino'''
assert ast.unparse(python_function("stable_file")) == '''def stable_file(left: os.stat_result, right: os.stat_result) -> bool:
    return same_file(left, right) and left.st_size == right.st_size and (left.st_mtime_ns == right.st_mtime_ns) and (left.st_ctime_ns == right.st_ctime_ns)'''
assert ast.unparse(python_function("read_bounded_utf8")) == r'''def read_bounded_utf8(path: Path) -> str:
    path_bytes = os.fsencode(path)
    if not path_bytes or len(path_bytes) >= MAX_PATH_BYTES or b'\x00' in path_bytes:
        raise OSError('invalid source path')
    named_before_open = retry_eintr(path.stat)
    if not stat.S_ISREG(named_before_open.st_mode):
        raise OSError('source path is not a regular file')
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_CLOEXEC', 0)
    descriptor = retry_eintr(os.open, path, flags)
    try:
        opened = retry_eintr(os.fstat, descriptor)
        if not stat.S_ISREG(opened.st_mode) or not same_file(named_before_open, opened):
            raise OSError('opened source differs from named file')
        if opened.st_size < 0:
            raise OSError('invalid source file size')
        if opened.st_size > MAX_SOURCE_BYTES:
            raise OSError('source file exceeds bounded reader limit')
        if opened.st_size != named_before_open.st_size:
            raise OSError('source file changed during open')
        named_after_open = retry_eintr(path.stat)
        if not same_file(opened, named_after_open):
            raise OSError('source path changed during open')
        initial_size = opened.st_size
        scratch_capacity = min(initial_size + 1, READ_CHUNK_BYTES)
        source_bytes = bytearray(initial_size)
        total_bytes = 0
        while True:
            remaining = MAX_SOURCE_BYTES - total_bytes
            capacity = min(remaining + 1, scratch_capacity)
            chunk = retry_eintr(os.read, descriptor, capacity)
            if not chunk:
                break
            if len(chunk) > capacity:
                raise OSError('read returned more bytes than requested')
            if len(chunk) > remaining:
                raise OSError('source file exceeds bounded reader limit')
            if total_bytes > initial_size or len(chunk) > initial_size - total_bytes:
                raise OSError('source file changed during read')
            source_bytes[total_bytes:total_bytes + len(chunk)] = chunk
            total_bytes += len(chunk)
            if capacity < READ_CHUNK_BYTES:
                current_opened = retry_eintr(os.fstat, descriptor)
                if not stable_file(opened, current_opened):
                    raise OSError('source file changed during read')
        if total_bytes > MAX_SOURCE_BYTES:
            raise OSError('source file exceeds bounded reader limit')
        final_opened = retry_eintr(os.fstat, descriptor)
        final_named = retry_eintr(path.stat)
        if not stable_file(opened, final_opened) or not stable_file(final_opened, final_named):
            raise OSError('source file changed during read')
    finally:
        os.close(descriptor)
    del source_bytes[total_bytes:]
    return source_bytes.decode('utf-8')'''
expected_python_top_level_types = [
    ast.Expr,
    ast.ImportFrom,
    ast.Import,
    ast.Import,
    ast.Import,
    ast.Assign,
    ast.Assign,
    ast.Assign,
    ast.Assign,
    ast.Try,
    ast.Assign,
    ast.FunctionDef,
    ast.FunctionDef,
    ast.FunctionDef,
    ast.FunctionDef,
    ast.Try,
    ast.Assign,
    ast.Assign,
    ast.If,
    ast.Expr,
]
assert [type(statement) for statement in tree.body] == expected_python_top_level_types
assert [tree.body[index].name for index in range(11, 15)] == [
    "same_file",
    "stable_file",
    "retry_eintr",
    "read_bounded_utf8",
]
assert ast.unparse(tree.body[10]) == "SOURCE_PATH = ROOT / 'src/app/report_output_serialization_helpers.elisa'"
assert ast.unparse(tree.body[16]) == "text = text.replace('\\r\\n', '\\n').replace('\\r', '\\n')"


def is_python_message_statement(statement, message, *, stderr):
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return False
    call = statement.value
    if not isinstance(call.func, ast.Name) or call.func.id != "print":
        return False
    if len(call.args) != 1 or not isinstance(call.args[0], ast.Constant):
        return False
    if call.args[0].value != message:
        return False
    if stderr:
        return (
            len(call.keywords) == 1
            and call.keywords[0].arg == "file"
            and isinstance(call.keywords[0].value, ast.Attribute)
            and isinstance(call.keywords[0].value.value, ast.Name)
            and call.keywords[0].value.value.id == "sys"
            and call.keywords[0].value.attr == "stderr"
        )
    return not call.keywords


def is_python_exit_statement(statement):
    if not isinstance(statement, ast.Raise) or not isinstance(statement.exc, ast.Call):
        return False
    call = statement.exc
    return (
        isinstance(call.func, ast.Name)
        and call.func.id == "SystemExit"
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Constant)
        and call.args[0].value == 1
        and not call.keywords
    )


python_error_messages = (
    "report serialization loop layout: unable to resolve script path",
    "report serialization loop layout: unable to read source file",
)
python_top_level_tries = [statement for statement in tree.body if isinstance(statement, ast.Try)]
assert len(python_top_level_tries) == len(python_error_messages)
python_try_contracts = (
    (
        "ROOT = Path(__file__).resolve().parents[1]",
        "(OSError, RuntimeError)",
        python_error_messages[0],
    ),
    (
        "text = read_bounded_utf8(SOURCE_PATH)",
        "(OSError, UnicodeError)",
        python_error_messages[1],
    ),
)
for statement, (try_body, exception_types, message) in zip(
    python_top_level_tries, python_try_contracts
):
    assert len(statement.body) == 1
    assert not statement.orelse and not statement.finalbody
    assert ast.unparse(statement.body[0]) == try_body
    assert len(statement.handlers) == 1
    handler = statement.handlers[0]
    assert ast.unparse(handler.type) == exception_types
    assert len(handler.body) == 2
    assert is_python_message_statement(handler.body[0], message, stderr=True)
    assert is_python_exit_statement(handler.body[1])

python_missing_fragment_guards = [
    statement
    for statement in tree.body
    if isinstance(statement, ast.If)
    and isinstance(statement.test, ast.Call)
    and isinstance(statement.test.func, ast.Name)
    and statement.test.func.id == "any"
]
assert len(python_missing_fragment_guards) == 1
python_missing_fragment_guard = python_missing_fragment_guards[0]
predicate = python_missing_fragment_guard.test
assert isinstance(predicate, ast.Call) and isinstance(predicate.func, ast.Name)
assert predicate.func.id == "any" and len(predicate.args) == 1 and not predicate.keywords
generator = predicate.args[0]
assert isinstance(generator, ast.GeneratorExp) and not generator.generators[0].ifs
assert len(generator.generators) == 1 and generator.generators[0].is_async == 0
assert isinstance(generator.generators[0].target, ast.Name)
assert generator.generators[0].target.id == "fragment"
assert isinstance(generator.generators[0].iter, ast.Name)
assert generator.generators[0].iter.id == "required"
comparison = generator.elt
assert isinstance(comparison, ast.Compare) and len(comparison.ops) == 1
assert isinstance(comparison.ops[0], ast.NotIn) and len(comparison.comparators) == 1
assert isinstance(comparison.left, ast.Name) and comparison.left.id == "fragment"
assert isinstance(comparison.comparators[0], ast.Name)
assert comparison.comparators[0].id == "text"
assert len(python_missing_fragment_guard.body) == 2
assert is_python_message_statement(
    python_missing_fragment_guard.body[0],
    "report serialization loop layout: expected bounded scan fragment is missing",
    stderr=True,
)
assert is_python_exit_statement(python_missing_fragment_guard.body[1])
assert is_python_message_statement(
    tree.body[-1],
    "report serialization loop layout: bounded scans remain correctly nested",
    stderr=False,
)
all_python_system_exit_raises = [
    statement
    for statement in ast.walk(tree)
    if isinstance(statement, ast.Raise)
    and isinstance(statement.exc, ast.Call)
    and isinstance(statement.exc.func, ast.Name)
    and statement.exc.func.id == "SystemExit"
]
expected_python_system_exit_raises = [
    statement.handlers[0].body[1] for statement in python_top_level_tries
] + [python_missing_fragment_guard.body[1]]
assert {id(statement) for statement in all_python_system_exit_raises} == {
    id(statement) for statement in expected_python_system_exit_raises
}
assert not any(
    isinstance(node, ast.Call)
    and (
        isinstance(node.func, ast.Name)
        and node.func.id in {"exit", "quit"}
        or isinstance(node.func, ast.Attribute)
        and node.func.attr == "exit"
    )
    for node in ast.walk(tree)
)

python_prints = sorted(
    (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ),
    key=lambda node: (node.lineno, node.col_offset),
)
python_events = []
for call in python_prints:
    assert len(call.args) == 1 and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)
    assert all(keyword.arg == "file" for keyword in call.keywords)
    channel = "stdout"
    for keyword in call.keywords:
        if keyword.arg == "file":
            assert (
                isinstance(keyword.value, ast.Attribute)
                and isinstance(keyword.value.value, ast.Name)
                and keyword.value.value.id == "sys"
                and keyword.value.attr == "stderr"
            )
            channel = "stderr"
    python_events.append((channel, call.args[0].value + "\n"))

elisa_events = []
for match in re.finditer(r'\b(write_stderr|print)\(\s*("(?:\\.|[^"\\])*")\s*\)', elisa_source):
    function, literal = match.groups()
    message = ast.literal_eval(literal)
    if function == "print":
        elisa_events.append(("stdout", message + "\n"))
    else:
        elisa_events.append(("stderr", message))
assert len(elisa_events) == len(re.findall(r"\b(?:write_stderr|print)\s*\(", elisa_source))
expected_events = [
    ("stderr", "report serialization loop layout: unable to resolve script path\n"),
    ("stderr", "report serialization loop layout: unable to read source file\n"),
    ("stderr", "report serialization loop layout: expected bounded scan fragment is missing\n"),
    ("stdout", "report serialization loop layout: bounded scans remain correctly nested\n"),
]
assert python_events == elisa_events == expected_events, (python_events, elisa_events)
assert (
    'script_file: Path = try path_real(Script::invocation_path()) else err:\n'
    '        _ = write_stderr("report serialization loop layout: unable to resolve script path\\n")\n'
    '        return 1i64'
) in elisa_source
assert (
    'source: sview = try read_text_bounded(source_file, PROOF_REPORT_OUTPUT_LOOP_LAYOUT_MAX_SOURCE_BYTES) else err:\n'
    '        _ = write_stderr("report serialization loop layout: unable to read source file\\n")\n'
    '        return 1i64'
) in elisa_source
assert (
    'if not proof_report_output_loop_layout_contains(normalized_source, fragment):\n'
    '            _ = write_stderr("report serialization loop layout: expected bounded scan fragment is missing\\n")'
) in elisa_source
assert (
    '    for fragment in required:\n'
    '        if not proof_report_output_loop_layout_contains(normalized_source, fragment):\n'
    '            _ = write_stderr("report serialization loop layout: expected bounded scan fragment is missing\\n")\n'
    '            return 1i64\n'
    '\n'
    '    print("report serialization loop layout: bounded scans remain correctly nested")\n'
    '    return 0i64'
) in elisa_source
candidate_main = elisa_source[elisa_source.index("def main("):]
assert len(re.findall(r"^\s*return\b", candidate_main, re.M)) == 4
required_value_lines = "\n".join(
    f"        {quote_elisa_string(fragment)}" + ("," if index + 1 < len(elisa_fragments) else "")
    for index, fragment in enumerate(elisa_fragments)
)
expected_candidate_main = r'''def main(arguments: darray[sview]) -> i64 can[Blocking.IO, Memory.Allocate, Abort.Panic, File.Read, Console.Write, Console.Format]:
    _ = arguments
    script_file: Path = try path_real(Script::invocation_path()) else err:
        _ = write_stderr("report serialization loop layout: unable to resolve script path\n")
        return 1i64
    script_directory: Path = script_file.parent()
    proof_root: Path = script_directory.parent()
    source_file: Path = proof_root.joinpath("src/app/report_output_serialization_helpers.elisa")

    source: sview = try read_text_bounded(source_file, PROOF_REPORT_OUTPUT_LOOP_LAYOUT_MAX_SOURCE_BYTES) else err:
        _ = write_stderr("report serialization loop layout: unable to read source file\n")
        return 1i64

    normalized_source: sview = source.replace("\r\n", "\n").replace("\r", "\n")
    required: darray[sview] = [
{required_values}
    ]
    for fragment in required:
        if not proof_report_output_loop_layout_contains(normalized_source, fragment):
            _ = write_stderr("report serialization loop layout: expected bounded scan fragment is missing\n")
            return 1i64

    print("report serialization loop layout: bounded scans remain correctly nested")
    return 0i64'''.format(required_values=required_value_lines)
assert candidate_main.rstrip() == expected_candidate_main

check_python_reader_contract(python_source)

print("report-output source guards pass; Python/ElisaScript runtime parity remains unqualified")
