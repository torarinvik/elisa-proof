"""Exercise bounded reads, mutation handling, and EINTR behavior of the active Python reference."""

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import runpy
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/test_report_output_loop_layout.py"
SOURCE = ROOT / "src/app/report_output_serialization_helpers.elisa"
SOURCE_BYTES = SOURCE.stat().st_size


def run_with_reader(reader, script=SCRIPT):
    original_read = os.read
    stdout = io.StringIO()
    stderr = io.StringIO()
    os.read = reader
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                runpy.run_path(str(script))
                status = 0
            except SystemExit as exit_status:
                status = exit_status.code
    finally:
        os.read = original_read
    return status, stdout.getvalue(), stderr.getvalue()


def run_with_size_change_before_open(script, target):
    original_open = os.open
    original_close = os.close
    resolved_target = target.resolve()
    opened_descriptors = []
    closed_descriptors = []
    changed = False

    def change_size_before_open(path, flags, *args):
        nonlocal changed
        is_target = Path(path).resolve() == resolved_target
        if is_target and not changed:
            changed = True
            target.write_bytes(target.read_bytes() + b" ")
        descriptor = original_open(path, flags, *args)
        if is_target:
            opened_descriptors.append(descriptor)
        return descriptor

    def track_close(descriptor):
        is_target = descriptor in opened_descriptors
        result = original_close(descriptor)
        if is_target:
            closed_descriptors.append(descriptor)
        return result

    stdout = io.StringIO()
    stderr = io.StringIO()
    os.open = change_size_before_open
    os.close = track_close
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                runpy.run_path(str(script))
                status = 0
            except SystemExit as exit_status:
                status = exit_status.code
    finally:
        os.open = original_open
        os.close = original_close
    return status, stdout.getvalue(), stderr.getvalue(), opened_descriptors, closed_descriptors


def run_with_size_growth_during_read(script, target):
    original_open = os.open
    original_read = os.read
    original_close = os.close
    resolved_target = target.resolve()
    opened_descriptors = []
    closed_descriptors = []
    changed = False

    def track_open(path, flags, *args):
        descriptor = original_open(path, flags, *args)
        if Path(path).resolve() == resolved_target:
            opened_descriptors.append(descriptor)
        return descriptor

    def grow_before_read(descriptor, requested):
        nonlocal changed
        if descriptor in opened_descriptors and not changed:
            changed = True
            target.write_bytes(target.read_bytes() + b" ")
        return original_read(descriptor, requested)

    def track_close(descriptor):
        is_target = descriptor in opened_descriptors
        result = original_close(descriptor)
        if is_target:
            closed_descriptors.append(descriptor)
        return result

    stdout = io.StringIO()
    stderr = io.StringIO()
    os.open = track_open
    os.read = grow_before_read
    os.close = track_close
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                runpy.run_path(str(script))
                status = 0
            except SystemExit as exit_status:
                status = exit_status.code
    finally:
        os.open = original_open
        os.read = original_read
        os.close = original_close
    return status, stdout.getvalue(), stderr.getvalue(), opened_descriptors, closed_descriptors


def run_with_metadata_change_during_read(script, target):
    original_open = os.open
    original_read = os.read
    original_fstat = os.fstat
    original_close = os.close
    resolved_target = target.resolve()
    opened_descriptors = []
    closed_descriptors = []
    target_fstat_calls = 0
    changed = False

    def track_open(path, flags, *args):
        descriptor = original_open(path, flags, *args)
        if Path(path).resolve() == resolved_target:
            opened_descriptors.append(descriptor)
        return descriptor

    def change_metadata_before_read(descriptor, requested):
        nonlocal changed
        if descriptor in opened_descriptors and not changed:
            changed = True
            before = target.stat()
            with target.open("r+b") as stream:
                stream.seek(0)
                stream.write(b" ")
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))
        return original_read(descriptor, requested)

    def count_target_fstat(descriptor):
        nonlocal target_fstat_calls
        if descriptor in opened_descriptors:
            target_fstat_calls += 1
        return original_fstat(descriptor)

    def track_close(descriptor):
        is_target = descriptor in opened_descriptors
        result = original_close(descriptor)
        if is_target:
            closed_descriptors.append(descriptor)
        return result

    stdout = io.StringIO()
    stderr = io.StringIO()
    os.open = track_open
    os.read = change_metadata_before_read
    os.fstat = count_target_fstat
    os.close = track_close
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                runpy.run_path(str(script))
                status = 0
            except SystemExit as exit_status:
                status = exit_status.code
    finally:
        os.open = original_open
        os.read = original_read
        os.fstat = original_fstat
        os.close = original_close
    return (
        status,
        stdout.getvalue(),
        stderr.getvalue(),
        opened_descriptors,
        closed_descriptors,
        target_fstat_calls,
    )


real_read = os.read
short_read_calls = 0
largest_requested = 0


def one_byte_read(descriptor, requested):
    global short_read_calls
    short_read_calls += 1
    return real_read(descriptor, min(requested, 1))


status, stdout, stderr = run_with_reader(one_byte_read)
assert status == 0, (status, stdout, stderr)
assert "bounded scans remain correctly nested" in stdout
assert short_read_calls == SOURCE_BYTES + 1, short_read_calls

attempted_reads = 0
successful_reads = 0
injected_interrupts = 0


def repeated_short_reads_with_interrupts(descriptor, requested):
    global attempted_reads, successful_reads, injected_interrupts
    current = attempted_reads
    attempted_reads += 1
    if current % 101 == 100:
        injected_interrupts += 1
        raise InterruptedError
    successful_reads += 1
    return real_read(descriptor, min(requested, 1))


status, stdout, stderr = run_with_reader(repeated_short_reads_with_interrupts)
assert status == 0, (status, stdout, stderr)
assert attempted_reads == successful_reads + injected_interrupts, attempted_reads
assert injected_interrupts > 0 and successful_reads == SOURCE_BYTES + 1
assert "bounded scans remain correctly nested" in stdout
assert not stderr

# A stable file at the full byte limit remains readable when the filesystem
# returns ordinary positive short reads.
with tempfile.TemporaryDirectory(prefix="elisa-report-read-budget-") as temporary:
    project = Path(temporary)
    script = project / "scripts/test_report_output_loop_layout.py"
    target = project / "src/app/report_output_serialization_helpers.elisa"
    script.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    source_bytes = SOURCE.read_bytes()
    maximum_bytes = 16_777_216
    assert len(source_bytes) <= maximum_bytes
    target.write_bytes(source_bytes + b" " * (maximum_bytes - len(source_bytes)))
    short_read_calls = 0

    def short_read_512_bytes(descriptor, requested):
        global short_read_calls, largest_requested
        short_read_calls += 1
        largest_requested = max(largest_requested, requested)
        return real_read(descriptor, min(requested, 512))

    status, stdout, stderr = run_with_reader(short_read_512_bytes, script)
    assert status == 0, (status, stdout, stderr)
    assert "bounded scans remain correctly nested" in stdout
    assert short_read_calls == maximum_bytes // 512 + 1, short_read_calls
    assert largest_requested == 16_384, largest_requested

# A same-inode size change after the initial stat but before open is rejected,
# and the opened descriptor is closed on the error path.
with tempfile.TemporaryDirectory(prefix="elisa-report-open-race-") as temporary:
    project = Path(temporary)
    script = project / "scripts/test_report_output_loop_layout.py"
    target = project / "src/app/report_output_serialization_helpers.elisa"
    script.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    target.write_bytes(SOURCE.read_bytes())
    before = target.stat()

    status, stdout, stderr, opened_descriptors, closed_descriptors = (
        run_with_size_change_before_open(script, target)
    )

    after = target.stat()
    assert before.st_dev == after.st_dev and before.st_ino == after.st_ino
    assert after.st_size == before.st_size + 1, (before.st_size, after.st_size)
    assert status == 1 and not stdout
    assert stderr == "report serialization loop layout: unable to read source file\n"
    assert len(opened_descriptors) == len(closed_descriptors) == 1
    assert opened_descriptors == closed_descriptors

# A same-size metadata change during a small-file read reaches the intermediate
# fstat check and fails before the final fstat can run.
with tempfile.TemporaryDirectory(prefix="elisa-report-read-metadata-") as temporary:
    project = Path(temporary)
    script = project / "scripts/test_report_output_loop_layout.py"
    target = project / "src/app/report_output_serialization_helpers.elisa"
    script.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    target.write_bytes(SOURCE.read_bytes())
    before = target.stat()
    assert before.st_size + 1 < 16_384

    (
        status,
        stdout,
        stderr,
        opened_descriptors,
        closed_descriptors,
        target_fstat_calls,
    ) = run_with_metadata_change_during_read(script, target)

    after = target.stat()
    assert before.st_dev == after.st_dev and before.st_ino == after.st_ino
    assert before.st_size == after.st_size
    assert before.st_mtime_ns != after.st_mtime_ns
    assert status == 1 and not stdout
    assert stderr == "report serialization loop layout: unable to read source file\n"
    assert len(opened_descriptors) == len(closed_descriptors) == 1
    assert opened_descriptors == closed_descriptors
    assert target_fstat_calls == 2, target_fstat_calls

# Growth after opening is rejected before bytes beyond the opened-size snapshot
# are retained, and the descriptor is closed on that failure path.
with tempfile.TemporaryDirectory(prefix="elisa-report-read-growth-") as temporary:
    project = Path(temporary)
    script = project / "scripts/test_report_output_loop_layout.py"
    target = project / "src/app/report_output_serialization_helpers.elisa"
    script.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    target.write_bytes(SOURCE.read_bytes())
    before = target.stat()

    status, stdout, stderr, opened_descriptors, closed_descriptors = (
        run_with_size_growth_during_read(script, target)
    )

    after = target.stat()
    assert before.st_dev == after.st_dev and before.st_ino == after.st_ino
    assert after.st_size == before.st_size + 1, (before.st_size, after.st_size)
    assert status == 1 and not stdout
    assert stderr == "report serialization loop layout: unable to read source file\n"
    assert len(opened_descriptors) == len(closed_descriptors) == 1
    assert opened_descriptors == closed_descriptors

# Repeated interruption still fails closed after the initial attempt plus the
# configured four retries.
interrupted_attempts = 0


def repeated_interruptions(descriptor, requested):
    global interrupted_attempts
    interrupted_attempts += 1
    raise InterruptedError


status, stdout, stderr = run_with_reader(repeated_interruptions)
assert status == 1 and "unable to read source file" in stderr, (status, stdout, stderr)
assert interrupted_attempts == 5, interrupted_attempts

print("report-output bounded reader: short/full-limit reads, pre-open and read-time mutation, and repeated EINTR behave correctly")
