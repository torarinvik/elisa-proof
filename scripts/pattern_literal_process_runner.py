"""Bound subprocess time and output for pattern-literal regression tests."""
import os
import selectors
import subprocess
import sys
import time
from pathlib import Path


PROCESS_TIMEOUT_SECONDS = 120
PROCESS_OUTPUT_LIMIT = 8 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]


def run(command, label, timeout_seconds=PROCESS_TIMEOUT_SECONDS):
    """Bound each prover invocation so a bad child cannot hang or exhaust this gate."""
    stdout = bytearray()
    stderr = bytearray()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.monotonic() + timeout_seconds
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, stdout)
            selector.register(process.stderr, selectors.EVENT_READ, stderr)
            output_size = 0
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f'{label} timed out after {timeout_seconds}s')
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    output_size += len(chunk)
                    if output_size > PROCESS_OUTPUT_LIMIT:
                        raise AssertionError(
                            f'{label} output exceeded {PROCESS_OUTPUT_LIMIT} bytes')
                    key.data.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f'{label} timed out after {timeout_seconds}s')
        returncode = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(
            command, returncode, stdout.decode('utf-8', errors='replace'),
            stderr.decode('utf-8', errors='replace'),
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(f'{label} timed out after {timeout_seconds}s') from error
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout is not None and not process.stdout.closed:
            process.stdout.close()
        if process.stderr is not None and not process.stderr.closed:
            process.stderr.close()


def verify_process_limits():
    noisy = [sys.executable, '-c',
             f"import sys; sys.stdout.write('x' * {PROCESS_OUTPUT_LIMIT + 1}); sys.stdout.flush()"]
    try:
        run(noisy, 'output-cap self-test', timeout_seconds=10)
    except AssertionError as error:
        assert 'output exceeded' in str(error), error
    else:
        raise AssertionError('pattern test runner accepted output beyond its shared cap')

    slow = [sys.executable, '-c', 'import time; time.sleep(2)']
    try:
        run(slow, 'timeout self-test', timeout_seconds=0.05)
    except AssertionError as error:
        assert 'timed out' in str(error), error
    else:
        raise AssertionError('pattern test runner accepted a child beyond its deadline')
