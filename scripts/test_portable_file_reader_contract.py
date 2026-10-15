"""Pin the Elisa boundary to the descriptor-checked, bounded native reader."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/app/portable_io.elisa").read_text(encoding="utf-8")
reader = source.split("def proof_read_file_checked_with_limit(", 1)[1].split(
    "\ndef proof_read_file_checked(", 1
)[0]
assert "extern proof_open_regular_readonly(path: cstr, snapshot: u64&) -> i64" in source
assert "extern proof_regular_file_stable(descriptor: i64, path: cstr, snapshot: u64&) -> i64" in source
assert "proof_open_regular_readonly(path, &file_snapshot[0])" in reader
c_reader = (ROOT / "src/app/portable_file_posix.c").read_text(encoding="utf-8")
assert "O_RDONLY | O_NONBLOCK" in c_reader
assert "stat(path, &named_before)" in c_reader
assert "fstat(fd, &opened)" in c_reader
assert "read_call_limit: usize = (max_bytes / PROOF_INPUT_FILE_CHUNK_SIZE + 2) * PROOF_INPUT_FILE_READ_CALLS_PER_CHUNK" in reader
assert "if read_calls >= read_call_limit:" in reader
assert "proof_regular_file_stable(descriptor, path, &file_snapshot[0]) != 0" in reader
assert reader.index("proof_regular_file_stable(") < reader.index("close(descriptor) == 0")
print("portable file reader source contract: bounded reads, descriptor/path identity, stability check")
