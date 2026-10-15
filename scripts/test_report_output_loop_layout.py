"""Catch malformed indentation in bounded report serialization scans."""
from pathlib import Path
import os
import stat
import sys

MAX_SOURCE_BYTES = 16_777_216
MAX_PATH_BYTES = 4096
try:
    ROOT = Path(__file__).resolve().parents[1]
except (OSError, RuntimeError):
    print("report serialization loop layout: unable to resolve script path", file=sys.stderr)
    raise SystemExit(1)

SOURCE_PATH = ROOT / "src/app/report_output_serialization_helpers.elisa"


def same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def stable_file(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        same_file(left, right)
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


def read_bounded_utf8(path: Path) -> str:
    path_bytes = os.fsencode(path)
    if not path_bytes or len(path_bytes) >= MAX_PATH_BYTES or b"\0" in path_bytes:
        raise OSError("invalid source path")
    named_before_open = path.stat()
    if not stat.S_ISREG(named_before_open.st_mode):
        raise OSError("source path is not a regular file")

    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not same_file(named_before_open, opened):
            raise OSError("opened source differs from named file")
        named_after_open = path.stat()
        if not same_file(opened, named_after_open):
            raise OSError("source path changed during open")

        chunks: list[bytes] = []
        remaining = MAX_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source_bytes = b"".join(chunks)
        if len(source_bytes) > MAX_SOURCE_BYTES:
            raise OSError("source file exceeds bounded reader limit")

        final_opened = os.fstat(descriptor)
        final_named = path.stat()
        if not stable_file(opened, final_opened) or not stable_file(final_opened, final_named):
            raise OSError("source file changed during read")
    finally:
        os.close(descriptor)

    return source_bytes.decode("utf-8")


try:
    text = read_bounded_utf8(SOURCE_PATH)
except (OSError, UnicodeError):
    print("report serialization loop layout: unable to read source file", file=sys.stderr)
    raise SystemExit(1)

text = text.replace("\r\n", "\n").replace("\r", "\n")

required = (
    "-> (complete: bool, index: usize):\n    for candidate in 0..<names.count",
    "-> (complete: bool, contains: bool):\n    for prior in 0..<count",
    "\n        return (false, names.count) if not proof_replay_fact_origin_text_compare_charge(names[candidate], name, work)",
    "\n        return (false, false) if not proof_replay_fact_origin_work_charge(1, work)",
)
if any(fragment not in text for fragment in required):
    print("report serialization loop layout: expected bounded scan fragment is missing", file=sys.stderr)
    raise SystemExit(1)

print("report serialization loop layout: bounded scans remain correctly nested")
