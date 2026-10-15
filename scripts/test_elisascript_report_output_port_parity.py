"""Pin source contracts for the active Python/ElisaScript port."""

import ast
import re
from pathlib import Path


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
interpreter_source = interpreter.read_text(encoding="utf-8")
lowerer_source = lowerer.read_text(encoding="utf-8")
ir_model_source = ir_model.read_text(encoding="utf-8")
verifier_source = verifier.read_text(encoding="utf-8")
registry_source = builtin_registry.read_text(encoding="utf-8")
bounded_reader = (ROOT.parent / "elisa-script/src/runtime/bounded_text_posix.elisa").read_text(encoding="utf-8")
reader_body = bounded_reader.split("def read_utf8(", 1)[1].split("def descriptor_shape", 1)[0]


def python_assignment(name: str):
    tree = ast.parse(python_source)
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in statement.targets
        ):
            return ast.literal_eval(statement.value)
    raise AssertionError(f"Python assignment {name} not found")


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
    "path_real(Script::source_path())",
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
assert "EsBoundedText::read_utf8(path(path_value.text), maximum_bytes)" in interpreter_source
assert "def read_utf8(input_path: Path, maximum_bytes: usize)" in bounded_reader
assert 'return try read_utf8_text(f"{input_path}", maximum_bytes)' in bounded_reader
assert "def read_utf8_text(input_path: sview" in bounded_reader
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
assert "READ_EINTR_RETRIES: usize = 4" in bounded_reader
assert "DarwinOpenFlags::NONBLOCK" in bounded_reader and "DarwinOpenFlags::CLOSE_ON_EXEC" in bounded_reader
assert "text_is_valid_utf8(contents)" in bounded_reader
assert "same_file(named_before_open, opened)" in reader_body
assert "same_file(opened, named_after_open)" in reader_body
assert "stable_file(opened, final_opened)" in reader_body
assert "stable_file(final_opened, final_named)" in reader_body
assert reader_body.index("if opened.size > maximum_bytes.i64():") < reader_body.index("named_after_open: mutable ElisascriptStat")
for helper_name in ("open_path", "stat_path", "fstat_descriptor"):
    helper_body = bounded_reader.split(f"def {helper_name}(", 1)[1].split("\n\n", 1)[0]
    assert "errno[0] == EsProcessExecSearch::DarwinErrno::EINTR" in helper_body, helper_name
    assert "retries < Limits::READ_EINTR_RETRIES" in helper_body, helper_name
assert "errno[0] == EsProcessExecSearch::DarwinErrno::EINTR and interrupted < Limits::READ_EINTR_RETRIES" in reader_body
assert "close_status: int = elisascript_posix_close(descriptor)" in reader_body
assert 'source.replace("\\r\\n", "\\n").replace("\\r", "\\n")' in elisa_source
assert "proof_report_output_loop_layout_contains(normalized_source, fragment)" in elisa_source
assert "failure: mutable darray[usize] = []" in elisa_source
assert "failure.reserve(needle_length)" in elisa_source
assert "failure[index] <- prefix_length" in elisa_source
assert "matched <- failure[matched - 1]" in elisa_source
assert "normalized_source.contains(fragment)" not in elisa_source

assert "read_text_bounded" in (ROOT.parent / "elisa-script/docs/semantics.md").read_text(encoding="utf-8")

python_messages = {
    ast.literal_eval(f'"{value}"') + "\n"
    for value in re.findall(r'print\("([^"\n]*)"(?:,\s*file=sys\.stderr)?\)', python_source)
}
elisa_messages = set()
for value in re.findall(r'(?:write_stderr|print)\("([^"\n]*)"\)', elisa_source):
    message = ast.literal_eval(f'"{value}"')
    elisa_messages.add(message if message.endswith("\n") else message + "\n")
assert python_messages == elisa_messages, (python_messages, elisa_messages)

assert python_assignment("MAX_SOURCE_BYTES") == 16_777_216
assert python_assignment("MAX_PATH_BYTES") == 4096
assert python_assignment("MAX_EINTR_RETRIES") == 4
python_reader = python_source.split("def read_bounded_utf8(", 1)[1].split("\n\ntry:", 1)[0]
assert "for retry in range(MAX_EINTR_RETRIES + 1):" in python_source
for operation in (
    "retry_eintr(path.stat)",
    "retry_eintr(os.open, path, flags)",
    "retry_eintr(os.fstat, descriptor)",
    "retry_eintr(os.read, descriptor, remaining)",
):
    assert operation in python_source, operation
assert "os.close(descriptor)" in python_source
assert "retry_eintr(os.close" not in python_source
assert 'getattr(os, "O_NONBLOCK"' in python_source and 'getattr(os, "O_CLOEXEC"' in python_source
assert 'b"\\0" in path_bytes' in python_source
assert "st_mtime_ns" in python_source and "st_ctime_ns" in python_source
assert "stat.S_ISREG" in python_source
assert "source_bytes.decode(\"utf-8\")" in python_source
assert "if opened.st_size > MAX_SOURCE_BYTES:" in python_reader
assert python_reader.index("if opened.st_size > MAX_SOURCE_BYTES:") < python_reader.index("named_after_open = retry_eintr(path.stat)")

print("report-output Python/ElisaScript source contracts match; runtime parity remains unqualified")
