"""Pin source-level behavior shared by the active Python and ElisaScript port."""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
python_reference = ROOT / "scripts/test_report_output_loop_layout.py"
elisa_counterpart = ROOT / "scripts/test_report_output_loop_layout.elisascript"
assert python_reference.parent == elisa_counterpart.parent
assert python_reference.stem == elisa_counterpart.stem
python_source = python_reference.read_text(encoding="utf-8")
elisa_source = elisa_counterpart.read_text(encoding="utf-8")
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

# The source-relative target must resolve identically from the Python reference and its
# colocated ElisaScript counterpart; otherwise matching fragment lists would check different files.
assert "Path(__file__).resolve().parents[1]" in python_source
assert 'include "../../elisa-script/vendor/elisa-compiler/elisacore_std/elisacore_runtime.elisa"' in elisa_source
assert "using EsRuntime" in elisa_source
for path_step in (
    "path_real(path(Script::source_path()))",
    "script_file.parent()",
    "proof_root: Path = script_directory.parent()",
    'proof_root.joinpath("src/app/report_output_serialization_helpers.elisa")',
):
    assert path_step in elisa_source, path_step
assert "def proof_report_output_loop_layout_contains(haystack: sview, needle: sview) -> bool can[Memory.Allocate, Abort.Panic]:" in elisa_source
assert "failure: mutable darray[usize] = []" in elisa_source
assert "failure.reserve(needle_length)" in elisa_source
assert "for index in 1..<needle_length |failure, needle, prefix_length|:" in elisa_source
assert "prefix_length <- failure[prefix_length - 1]" in elisa_source
assert "for index in 0..<haystack_length |haystack, needle, failure, matched|:" in elisa_source
assert "return true if matched == needle_length" in elisa_source
assert "normalized_bytes.reserve(sview_len(source))" in elisa_source
assert "while normalization_offset < sview_len(source):" in elisa_source
assert "if current_byte == 13u8:" in elisa_source
assert "normalized_bytes.push(10u8)" in elisa_source
assert "sview_at(source, normalization_offset) == 10u8" in elisa_source
assert "normalized_source: sview = bytes_view(normalized_bytes)" in elisa_source
assert ".replace(" not in elisa_source and ".index(" not in elisa_source
assert "File.Read" not in elisa_source and "Directory.Read" not in elisa_source

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
assert "EsBoundedText::read_utf8(source_file, 16777216)" in elisa_source
assert "MAX_BYTES: usize = 16777216" in bounded_reader
assert "PATH_BYTES: usize = 4096" in bounded_reader
assert "READ_EINTR_RETRIES: usize = 4" in bounded_reader
assert "close_status: int = elisascript_posix_close(descriptor)" in bounded_reader
assert "chunk_capacity: mutable usize = maximum_bytes + 1" in bounded_reader
assert "initial_capacity: mutable usize = maximum_bytes if maximum_bytes < Limits::READ_CHUNK_BYTES else Limits::READ_CHUNK_BYTES" in reader_body
assert "initial_capacity <- opened.size.usize() if opened.size.usize() < maximum_bytes" in reader_body
assert "opened.size < 0" in reader_body
assert "if opened.size > maximum_bytes.i64():" in reader_body
assert reader_body.index("if opened.size > maximum_bytes.i64():") < reader_body.index("chunk: mutable darray[u8] = []")
assert "chunk_capacity <- opened.size.usize() + 1 if opened.size.usize() < maximum_bytes" in reader_body
assert "chunk_capacity <- Limits::READ_CHUNK_BYTES if chunk_capacity > Limits::READ_CHUNK_BYTES" in bounded_reader
assert "chunk.reserve(chunk_capacity)" in bounded_reader
assert "for _ in 0..<chunk_capacity |chunk|:" in bounded_reader
assert reader_body.index("raise ReadError.LimitExceeded if maximum_bytes > Limits::MAX_BYTES") < reader_body.index("chunk_capacity: mutable usize = maximum_bytes + 1")
assert reader_body.index("chunk_capacity <- opened.size.usize() + 1") < reader_body.index("chunk_capacity <- Limits::READ_CHUNK_BYTES") < reader_body.index("chunk.reserve(chunk_capacity)")
assert reader_body.index("initial_capacity <- opened.size.usize()") < reader_body.index("bytes.reserve(initial_capacity)")
assert reader_body.index("if read_count > remaining:") < reader_body.index("for offset in 0..<read_count |bytes, chunk|:")
assert 'getattr(os, "O_NONBLOCK"' in python_source and 'getattr(os, "O_CLOEXEC"' in python_source
assert "DarwinOpenFlags::NONBLOCK" in bounded_reader and "DarwinOpenFlags::CLOSE_ON_EXEC" in bounded_reader
assert "b\"\\0\" in path_bytes" in python_source
assert "sview_contains_byte(path_text, 0)" in bounded_reader
assert "st_mtime_ns" in python_source and "st_ctime_ns" in python_source
for timestamp_field in ("modify_time", "change_time"):
    assert f"left.{timestamp_field}.seconds == right.{timestamp_field}.seconds" in bounded_reader
    assert f"left.{timestamp_field}.nanoseconds == right.{timestamp_field}.nanoseconds" in bounded_reader
assert "stat.S_ISREG" in python_source and "DarwinStatMode::REGULAR" in bounded_reader
assert 'text.replace("\\r\\n", "\\n").replace("\\r", "\\n")' in python_source
assert 'source_bytes.decode("utf-8")' in python_source
assert "text_is_valid_utf8(contents)" in bounded_reader
assert "The returned view owns permanent backing storage so it can outlive this reader frame." in bounded_reader
assert "owned_text: cstr = string_view_copy(contents)" in bounded_reader
assert "return sview(owned_bytes, 0, len(contents).i64())" in bounded_reader
assert bounded_reader.index("text_is_valid_utf8(contents)") < bounded_reader.index("owned_text: cstr = string_view_copy(contents)") < bounded_reader.index("return sview(owned_bytes, 0, len(contents).i64())")

print("report-output Python/ElisaScript port: fragments, diagnostics, UTF-8 and bounds match")
