"""Check the Python reference's bounded UTF-8 reader contract."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check_python_reader_contract(python_source: str) -> None:
    tree = ast.parse(python_source)

    def assignment(name: str):
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in statement.targets
            ):
                return ast.literal_eval(statement.value)
        raise AssertionError(f"Python assignment {name} not found")

    assert assignment("MAX_SOURCE_BYTES") == 16_777_216
    assert assignment("MAX_PATH_BYTES") == 4096
    assert assignment("MAX_EINTR_RETRIES") == 4
    assert assignment("READ_CHUNK_BYTES") == 16_384

    reader = python_source.split("def read_bounded_utf8(", 1)[1].split("\n\ntry:", 1)[0]
    assert "initial_size = opened.st_size" in reader
    assert "scratch_capacity = min(initial_size + 1, READ_CHUNK_BYTES)" in reader
    assert (
        "while True:\n"
        "            remaining = MAX_SOURCE_BYTES - total_bytes\n"
        "            capacity = min(remaining + 1, scratch_capacity)\n"
        "            chunk = retry_eintr(os.read, descriptor, capacity)"
    ) in reader
    assert "source_bytes = bytearray(initial_size)" in reader
    assert "source_bytes[total_bytes : total_bytes + len(chunk)] = chunk" in reader
    assert "del source_bytes[total_bytes:]" in reader
    assert "chunks: list[bytes]" not in reader and "b\"\".join(chunks)" not in reader
    assert "if len(chunk) > capacity:" in reader
    assert "if len(chunk) > remaining:" in reader
    assert "if total_bytes > initial_size or len(chunk) > initial_size - total_bytes:" in reader
    assert reader.index("if total_bytes > initial_size or len(chunk) > initial_size - total_bytes:") < reader.index(
        "source_bytes[total_bytes : total_bytes + len(chunk)] = chunk"
    )
    assert (
        "if capacity < READ_CHUNK_BYTES:\n"
        "                current_opened = retry_eintr(os.fstat, descriptor)\n"
        "                if not stable_file(opened, current_opened):"
    ) in reader
    assert "read_call_limit" not in reader
    assert "for retry in range(MAX_EINTR_RETRIES + 1):" in python_source

    retry_function = next(
        statement
        for statement in tree.body
        if isinstance(statement, ast.FunctionDef) and statement.name == "retry_eintr"
    )
    assert len(retry_function.body) == 2
    retry_loop, retry_terminal_raise = retry_function.body
    assert isinstance(retry_loop, ast.For) and isinstance(retry_loop.target, ast.Name)
    assert retry_loop.target.id == "retry"
    assert ast.unparse(retry_loop.iter) == "range(MAX_EINTR_RETRIES + 1)"
    assert len(retry_loop.body) == 1 and not retry_loop.orelse
    retry_try = retry_loop.body[0]
    assert isinstance(retry_try, ast.Try) and not retry_try.orelse and not retry_try.finalbody
    assert len(retry_try.body) == 1 and isinstance(retry_try.body[0], ast.Return)
    retry_call = retry_try.body[0].value
    assert isinstance(retry_call, ast.Call) and isinstance(retry_call.func, ast.Name)
    assert retry_call.func.id == "operation" and not retry_call.keywords
    assert len(retry_call.args) == 1 and isinstance(retry_call.args[0], ast.Starred)
    assert isinstance(retry_call.args[0].value, ast.Name) and retry_call.args[0].value.id == "args"
    assert len(retry_try.handlers) == 1
    retry_handler = retry_try.handlers[0]
    assert ast.unparse(retry_handler.type) == "InterruptedError"
    assert len(retry_handler.body) == 1 and isinstance(retry_handler.body[0], ast.If)
    retry_limit_check = retry_handler.body[0]
    assert ast.unparse(retry_limit_check.test) == "retry == MAX_EINTR_RETRIES"
    assert not retry_limit_check.orelse
    assert len(retry_limit_check.body) == 1 and isinstance(retry_limit_check.body[0], ast.Raise)
    assert retry_limit_check.body[0].exc is None
    assert isinstance(retry_terminal_raise, ast.Raise) and isinstance(retry_terminal_raise.exc, ast.Call)
    retry_terminal_call = retry_terminal_raise.exc
    assert isinstance(retry_terminal_call.func, ast.Name) and retry_terminal_call.func.id == "OSError"
    assert len(retry_terminal_call.args) == 1 and not retry_terminal_call.keywords
    assert isinstance(retry_terminal_call.args[0], ast.Constant)
    assert retry_terminal_call.args[0].value == "interrupted operation retry limit reached"

    for operation in (
        "retry_eintr(path.stat)",
        "retry_eintr(os.open, path, flags)",
        "retry_eintr(os.fstat, descriptor)",
    ):
        assert operation in python_source, operation
    assert "chunk = retry_eintr(os.read, descriptor, capacity)" in reader
    assert "chunk = retry_eintr(os.read, descriptor, capacity)\n            if not chunk:" in reader
    assert "os.close(descriptor)" in python_source
    assert "retry_eintr(os.close" not in python_source
    assert 'getattr(os, "O_NONBLOCK"' in python_source and 'getattr(os, "O_CLOEXEC"' in python_source
    assert 'b"\\0" in path_bytes' in python_source
    assert "st_mtime_ns" in python_source and "st_ctime_ns" in python_source
    assert "stat.S_ISREG" in python_source
    assert 'source_bytes.decode("utf-8")' in python_source
    assert "if opened.st_size > MAX_SOURCE_BYTES:" in reader
    size_snapshot_check = (
        "if opened.st_size != named_before_open.st_size:\n"
        "            raise OSError(\"source file changed during open\")"
    )
    assert size_snapshot_check in reader
    assert (
        reader.index("if opened.st_size > MAX_SOURCE_BYTES:")
        < reader.index(size_snapshot_check)
        < reader.index("named_after_open = retry_eintr(path.stat)")
    )


def main() -> None:
    reference = ROOT / "scripts/test_report_output_loop_layout.py"
    check_python_reader_contract(reference.read_text(encoding="utf-8"))
    print("report-output Python bounded-reader contract passes")


if __name__ == "__main__":
    main()
