"""Shared `--json` runner for the Python tests: reads scripts/test.sh's prefetched reports and runs
the rest in parallel.

scripts/test.sh exports ELISA_PROOF_REPORT_CACHE when ELISA_PROOF_JOBS>1; its entries were made
by scripts/prefetch_reports.py with ELISA_PROOF_BIN in this same run, so a cached entry is
reused only for that binary. Soundness incidents or incomplete incident classification disable
report reuse and prefetch until semantic rule coverage is available. Anything else runs the
selected verifier as before.
"""
import concurrent.futures
import contextlib
import fcntl
import hashlib
import json
import locale
import os
import platform
import re
import selectors
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from soundness_incident_registry import registry_allows_unqualified_reuse
from strict_json import loads as strict_json_loads

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BINARY = Path(os.environ.get("ELISA_PROOF_BIN") or ROOT / "build/elisa-proof")
REPORT_CACHE_SCHEMA = b"elisa-proof-report-cache-v5\0"
INCLUDE_RE = re.compile(r'^\s*include\s+"([^"]+)"', re.MULTILINE)
PENDING_WAIT_SECONDS = 10.0
MAX_CACHED_REPORT_BYTES = 64 * 1024 * 1024
MAX_DIRECT_REPORT_OUTPUT_BYTES = 128 * 1024 * 1024
MAX_VERIFIER_SECONDS = 600
MAX_REPORT_SOURCE_BYTES = 16 * 1024 * 1024
MAX_REPORT_IDENTITY_SOURCE_BYTES = 256 * 1024 * 1024
MAX_REPORT_IDENTITY_FILES = 16_384
MAX_REPORT_INCLUDE_REFERENCES = 65_536
MAX_SOUNDNESS_REGISTRY_BYTES = 1024 * 1024
MAX_CACHE_DIGEST_BYTES = 128
MAX_CACHE_STATUS_BYTES = 32
REPORT_CACHE_RECIPES = (
    Path(__file__).resolve(),
    ROOT / "scripts/prefetch_reports.py",
    ROOT / "scripts/strict_json.py",
)
SOUNDNESS_INCIDENT_REGISTRY = Path(__file__).with_name("soundness_incidents.json")
SOUNDNESS_INCIDENT_POLICY = Path(__file__).with_name("soundness_incident_registry.py")


class CacheIdentityUnavailable(ValueError):
    """The complete cache identity could not be read reliably; run verification directly."""


def _cache_identity_sha256(path: Path) -> str:
    try:
        return _sha256_regular_file(path)
    except OSError as error:
        raise CacheIdentityUnavailable(f"cache identity input is unavailable: {path}") from error


def _cache_identity_snapshot(path: Path):
    try:
        return _sha256_regular_file(path, include_stat=True)
    except OSError as error:
        raise CacheIdentityUnavailable(f"cache identity input is unavailable: {path}") from error


def soundness_registry_allows_report_reuse(raw_registry=None) -> bool:
    """Fail closed until every soundness report is classified for exact products.

    Report-cache metadata has no complete semantic-rule inventory yet. Therefore even confirmed
    incidents disable report reuse globally; matching only the executable digest would be too
    weak to decide whether its cached theorem claims traverse the affected rule.
    """
    if raw_registry is None:
        raw_registry = _read_bounded_regular_file(
            SOUNDNESS_INCIDENT_REGISTRY, MAX_SOUNDNESS_REGISTRY_BYTES
        )
    if raw_registry is None:
        return False
    try:
        registry = strict_json_loads(raw_registry)
    except (UnicodeError, ValueError):
        return False
    return registry_allows_unqualified_reuse(registry)


def _file_identity(file_stat):
    return file_stat.st_dev, file_stat.st_ino


def _open_regular_file_without_symlink(path):
    """Open a regular file and verify its inode around open.

    `O_NOFOLLOW` and lstat/fstat checks reject path substitution where available; nonblocking
    open lets the regular-file check reject FIFOs without hanging.
    """
    path_before = os.lstat(path)
    if not stat.S_ISREG(path_before.st_mode):
        raise OSError("cache input is not a regular file")
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
    )
    try:
        opened = os.fstat(descriptor)
        path_after = os.lstat(path)
        if not stat.S_ISREG(opened.st_mode) or not stat.S_ISREG(path_after.st_mode) \
                or _file_identity(path_before) != _file_identity(opened) \
                or _file_identity(path_after) != _file_identity(opened):
            raise OSError("cache input changed or is not a regular file")
        return descriptor, opened
    except BaseException:
        os.close(descriptor)
        raise


def _sha256_regular_file(path: Path, max_bytes: int | None = None, *, include_stat=False):
    """Hash a regular file without allocating its contents; reject observed mutation."""
    descriptor = None
    try:
        descriptor, before = _open_regular_file_without_symlink(path)
        if max_bytes is not None and (before.st_size < 0 or before.st_size > max_bytes):
            raise OSError("cache identity input exceeds its size limit")
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                total += len(chunk)
                if max_bytes is not None and total > max_bytes:
                    raise OSError("cache identity input exceeds its size limit")
                digest.update(chunk)
        after = os.fstat(descriptor)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                before.st_dev, before.st_ino, before.st_size,
                before.st_mtime_ns, before.st_ctime_ns):
            raise OSError("cache identity input changed while hashing")
        path_after = os.lstat(path)
        if not stat.S_ISREG(path_after.st_mode) or _file_identity(path_after) != _file_identity(after):
            raise OSError("cache identity path changed while hashing")
        if total != before.st_size:
            raise OSError("cache identity input size changed while hashing")
        identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        return (digest.hexdigest(), identity) if include_stat else digest.hexdigest()
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _report_inputs(path, binary, recipe_files=None, registry_bytes=None):
    """Return the complete identity inputs for one report.

    Reports depend on the fixture and every textually included file, the exact executable, and
    mode/loader settings inherited from the environment. Cache files may be shared between
    workers, so directory-local assumptions are not an identity boundary.
    """
    visited = set()
    pending = [Path(os.path.realpath(str(path)))]
    inputs = []
    source_bytes = 0
    include_references = 0
    while pending:
        current = pending.pop()
        identity = os.path.realpath(str(current))
        if identity in visited:
            continue
        if len(visited) >= MAX_REPORT_IDENTITY_FILES:
            raise CacheIdentityUnavailable("report source identity exceeds its file-count limit")
        visited.add(identity)
        try:
            Path(identity).stat()
        except FileNotFoundError:
            inputs.append((identity, None))
            continue
        except OSError as error:
            raise CacheIdentityUnavailable(f"cannot inspect report source input: {identity}") from error
        snapshot = _read_bounded_regular_file(identity, MAX_REPORT_SOURCE_BYTES, include_stat=True)
        if snapshot is None:
            raise CacheIdentityUnavailable(f"report source input is unreadable, unstable, or oversized: {identity}")
        data, file_identity = snapshot
        if len(data) > MAX_REPORT_IDENTITY_SOURCE_BYTES - source_bytes:
            raise CacheIdentityUnavailable("report source identity exceeds its aggregate size limit")
        source_bytes += len(data)
        inputs.append((identity, hashlib.sha256(data).hexdigest(), file_identity))
        try:
            source = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for include_match in INCLUDE_RE.finditer(source):
            if include_references >= MAX_REPORT_INCLUDE_REFERENCES:
                raise CacheIdentityUnavailable("report source identity exceeds its include-reference limit")
            include_references += 1
            pending.append(current.parent / include_match.group(1))
    executable = os.path.realpath(str(binary))
    binary_digest, binary_identity = _cache_identity_snapshot(Path(executable))
    orchestration_env = {
        "ELISA_PROOF_REPORT_CACHE", "ELISA_PROOF_JOBS", "ELISA_PROOF_HEAVY_JOBS",
        "ELISA_PROOF_SHARDS", "ELISA_PROOF_PREFETCH_PHASE",
    }
    relevant_env = {
        key: value for key, value in os.environ.items()
        if key not in orchestration_env and
        (key.startswith(("ELISA_", "LD_", "DYLD_")) or key in ("LANG", "LC_ALL"))
    }
    recipe_inputs = []
    for recipe in recipe_files if recipe_files is not None else REPORT_CACHE_RECIPES:
        recipe_path = Path(os.path.realpath(str(recipe)))
        recipe_digest, recipe_identity = _cache_identity_snapshot(recipe_path)
        recipe_inputs.append((str(recipe_path), recipe_digest, recipe_identity))
    registry_snapshot = _read_bounded_regular_file(
        SOUNDNESS_INCIDENT_REGISTRY, MAX_SOUNDNESS_REGISTRY_BYTES, include_stat=True
    )
    if registry_snapshot is None:
        raise CacheIdentityUnavailable("soundness incident registry is unreadable or unstable")
    current_registry_bytes, registry_identity = registry_snapshot
    if registry_bytes is not None and registry_bytes != current_registry_bytes:
        raise CacheIdentityUnavailable("soundness incident registry changed during cache identity")
    registry_bytes = current_registry_bytes
    policy_digest, policy_identity = _cache_identity_snapshot(SOUNDNESS_INCIDENT_POLICY)
    return {
        "schema": 5,
        "fixture": os.path.realpath(str(path)),
        "inputs": sorted(inputs),
        "binary": executable,
        "binary_sha256": binary_digest,
        "binary_identity": binary_identity,
        "target": {"system": platform.system(), "machine": platform.machine()},
        "environment": relevant_env,
        "cache_recipes": sorted(recipe_inputs),
        "soundness_incident_registry": {
            "path": os.path.realpath(str(SOUNDNESS_INCIDENT_REGISTRY)),
            "sha256": hashlib.sha256(registry_bytes).hexdigest()
            if registry_bytes is not None else None,
            "identity": registry_identity,
            "policy_path": os.path.realpath(str(SOUNDNESS_INCIDENT_POLICY)),
            "policy_sha256": policy_digest,
            "policy_identity": policy_identity,
        },
    }


# A fixture that includes the kernel sources (or is large) peaks at ~2.7 GB of memory; the
# runner shares a few slots for them across every process of one test run, so a 12-core box with
# 8 GB does not run out. ELISA_PROOF_HEAVY_JOBS overrides the slot count.
HEAVY_PEAK_KB = 2_800_000


def is_heavy(path) -> bool:
    try:
        source_path = Path(path)
        if source_path.stat().st_size > 20_000:
            return True
        source_bytes = _read_bounded_regular_file(source_path, 20_000)
        if source_bytes is None:
            return True
        source = source_bytes.decode("utf-8")
        return re.search(r'^include "\.\./src/', source, re.MULTILINE) is not None
    except OSError:
        return True
    except UnicodeDecodeError:
        return True


def effective_cpus() -> int:
    """CPUs this process may actually use: the cgroup quota (cpu.max) when one is set, else nproc.
    Rented containers often report 80 cores but are throttled to a fraction of them."""
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count() or 1
    try:
        with open("/sys/fs/cgroup/cpu.max", encoding="utf-8") as limit:
            quota, period = limit.read().split()
        if quota != "max":
            cpus = min(cpus, max(1, int(quota) // int(period)))
    except (OSError, ValueError):
        pass
    # cgroup v1 hosts (e.g. a vast box showing 80 cores with a 38-CPU quota) keep it here.
    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us", encoding="utf-8") as quota_file, \
                open("/sys/fs/cgroup/cpu/cpu.cfs_period_us", encoding="utf-8") as period_file:
            quota, period = int(quota_file.read()), int(period_file.read())
        if quota > 0 and period > 0:
            cpus = min(cpus, max(1, quota // period))
    except (OSError, ValueError):
        pass
    return cpus


def heavy_slots() -> int:
    if "ELISA_PROOF_HEAVY_JOBS" in os.environ:
        return max(1, int(os.environ["ELISA_PROOF_HEAVY_JOBS"]))
    try:
        with open("/proc/meminfo", encoding="utf-8") as info:
            total_kb = int(re.search(r"MemTotal:\s+(\d+)", info.read()).group(1))
    except (OSError, AttributeError):
        total_kb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // 1024
    try:
        with open("/sys/fs/cgroup/memory.max", encoding="utf-8") as limit:
            value = limit.read().strip()
        if value != "max":
            total_kb = min(total_kb, int(value) // 1024)
    except (OSError, ValueError):
        pass
    # Keep a quarter of memory for the light fixtures and the system.
    return max(1, (total_kb * 3 // 4) // HEAVY_PEAK_KB)


@contextlib.contextmanager
def heavy_slot(path, lock_dir=None, force=False):
    """Hold one of the shared heavy-fixture slots while running `path`, if it is heavy (or forced)."""
    lock_dir = lock_dir or os.environ.get("ELISA_PROOF_REPORT_CACHE")
    if not lock_dir or not (force or is_heavy(path)):
        yield
        return
    os.makedirs(os.path.join(lock_dir, "slots"), exist_ok=True)
    slots = heavy_slots()
    while True:
        for index in range(slots):
            handle = open(os.path.join(lock_dir, "slots", str(index)), "w")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                continue
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
                handle.close()
            return
        time.sleep(0.5)  # poll-ok: waiting for a local heavy-fixture slot


def cache_key(path, binary=DEFAULT_BINARY, recipe_files=None, registry_bytes=None) -> str:
    payload = json.dumps(
        _report_inputs(path, binary, recipe_files, registry_bytes),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(REPORT_CACHE_SCHEMA + payload).hexdigest()


def _read_bounded_regular_file(path, max_bytes, *, include_stat=False):
    descriptor = None
    try:
        descriptor, file_stat = _open_regular_file_without_symlink(path)
        if file_stat.st_size < 0 or file_stat.st_size > max_bytes:
            return None
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            payload = source.read(max_bytes + 1)
        after_stat = os.fstat(descriptor)
        path_after = os.lstat(path)
        if len(payload) != file_stat.st_size or len(payload) > max_bytes \
                or not stat.S_ISREG(path_after.st_mode) \
                or _file_identity(path_after) != _file_identity(after_stat) \
                or (after_stat.st_dev, after_stat.st_ino, after_stat.st_size,
                    after_stat.st_mtime_ns, after_stat.st_ctime_ns) != (
                    file_stat.st_dev, file_stat.st_ino, file_stat.st_size,
                    file_stat.st_mtime_ns, file_stat.st_ctime_ns):
            return None
        identity = (after_stat.st_dev, after_stat.st_ino, after_stat.st_size,
                    after_stat.st_mtime_ns, after_stat.st_ctime_ns)
        return (payload, identity) if include_stat else payload
    except OSError:
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_cached_entry(entry):
    payload_bytes = _read_bounded_regular_file(entry + ".json", MAX_CACHED_REPORT_BYTES)
    digest_bytes = _read_bounded_regular_file(entry + ".sha256", MAX_CACHE_DIGEST_BYTES)
    status_bytes = _read_bounded_regular_file(entry + ".rc", MAX_CACHE_STATUS_BYTES)
    if payload_bytes is None or digest_bytes is None or status_bytes is None:
        return None
    try:
        digest = digest_bytes.decode("ascii").strip()
        status = int(status_bytes.decode("ascii").strip())
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            return None
        if hashlib.sha256(payload_bytes).hexdigest() != digest:
            return None
        payload = payload_bytes.decode("utf-8")
        report = strict_json_loads(payload)
        if not isinstance(report, dict):
            return None
        expected = 0 if report.get("status") == "proved" else 1 if report.get("status") == "failed" else None
        if expected is None or status != expected:
            return None
        return status, payload
    except (OSError, ValueError, TypeError, UnicodeDecodeError):
        return None


def _run_bounded_stdout(command, output, max_bytes, timeout, cwd=None):
    """Run a verifier while bounding captured stdout and terminating its process group on timeout."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=cwd,
        start_new_session=True,
    )
    written = 0
    exceeded = False
    write_failed = False
    reader = process.stdout
    selector = None
    eof = False
    deadline = None if timeout is None else time.monotonic() + timeout
    timed_out = False
    stop_process = False
    try:
        descriptor = reader.fileno()
        os.set_blocking(descriptor, False)
        selector = selectors.DefaultSelector()
        selector.register(descriptor, selectors.EVENT_READ)
        while True:
            if eof:
                if process.poll() is not None:
                    break
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    timed_out = True
                    break
                try:
                    process.wait(timeout=0.05 if remaining is None else min(0.05, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                timed_out = True
                break
            try:
                events = selector.select(remaining)
            except InterruptedError:
                continue
            except OSError:
                write_failed = True
                stop_process = True
                break
            for key, _ in events:
                try:
                    chunk = os.read(key.fd, 64 * 1024)
                except BlockingIOError:
                    continue
                except OSError:
                    write_failed = True
                    stop_process = True
                    break
                if not chunk:
                    selector.unregister(key.fd)
                    eof = True
                    continue
                remaining_bytes = max_bytes - written
                if remaining_bytes <= 0:
                    exceeded = stop_process = True
                    break
                accepted = chunk[:remaining_bytes]
                try:
                    output.write(accepted)
                except OSError:
                    write_failed = stop_process = True
                else:
                    written += len(accepted)
                if len(chunk) > len(accepted):
                    exceeded = stop_process = True
                    break
            if stop_process:
                break
    except OSError:
        write_failed = True
        stop_process = True
    except BaseException:
        stop_process = True
        raise
    finally:
        try:
            if selector is not None:
                selector.close()
        finally:
            try:
                reader.close()
            finally:
                if timed_out or stop_process:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except OSError:
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                return_code = process.wait()
                try:
                    output.flush()
                except OSError:
                    write_failed = True
    return return_code, written, exceeded, write_failed, timed_out


def _cached(binary, path):
    cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
    if not cache or os.path.realpath(str(binary)) != os.path.realpath(str(DEFAULT_BINARY)):
        return None
    registry_bytes = _read_bounded_regular_file(
        SOUNDNESS_INCIDENT_REGISTRY, MAX_SOUNDNESS_REGISTRY_BYTES
    )
    if not soundness_registry_allows_report_reuse(registry_bytes):
        return None
    try:
        key = cache_key(path, binary, registry_bytes=registry_bytes)
    except CacheIdentityUnavailable:
        return None
    entry = os.path.join(cache, key)
    pending = os.path.join(cache, "pending", key)

    def still_current(candidate):
        if candidate is None:
            return None
        current_registry = _read_bounded_regular_file(
            SOUNDNESS_INCIDENT_REGISTRY, MAX_SOUNDNESS_REGISTRY_BYTES
        )
        if not soundness_registry_allows_report_reuse(current_registry):
            return None
        try:
            current_key = cache_key(path, binary, registry_bytes=current_registry)
        except CacheIdentityUnavailable:
            return None
        return candidate if current_key == key else None

    hit = _read_cached_entry(entry)
    if hit is not None:
        return still_current(hit)
    if not os.path.exists(pending):
        return None
    # A prefetch may publish a report while a reader arrives. Wait only for a bounded interval;
    # crashed prefetchers can leave markers behind indefinitely.
    deadline = time.monotonic() + PENDING_WAIT_SECONDS
    while os.path.exists(pending) and time.monotonic() < deadline:
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
        hit = _read_cached_entry(entry)
        if hit is not None:
            return still_current(hit)
    return None


def json_run(path, binary=DEFAULT_BINARY, timeout=MAX_VERIFIER_SECONDS):
    """(returncode, stdout) of `binary --json path`, from the prefetch cache when it has it."""
    hit = _cached(binary, path)
    if hit is not None:
        return hit
    with heavy_slot(path):
        with tempfile.TemporaryFile(mode="w+b") as output:
            status, _, exceeded, write_failed, timed_out = _run_bounded_stdout(
                [str(binary), "--json", str(path)], output,
                MAX_DIRECT_REPORT_OUTPUT_BYTES, timeout,
            )
            if timed_out:
                raise subprocess.TimeoutExpired([str(binary), "--json", str(path)], timeout)
            if exceeded:
                return 125, "proof verifier output exceeded the configured size limit\n"
            if write_failed:
                return 125, "proof verifier output could not be captured\n"
            output.seek(0)
            try:
                text = output.read().decode(locale.getpreferredencoding(False))
            except UnicodeDecodeError:
                return 125, "proof verifier output was not valid text\n"
    return status, text


def json_runs(paths, binary=DEFAULT_BINARY, timeout=600):
    """json_run over many fixtures in parallel, results in input order."""
    jobs = max(1, int(os.environ.get("ELISA_PROOF_JOBS", effective_cpus())))
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(lambda p: json_run(p, binary, timeout), paths))


if __name__ == "__main__":
    # `report_cache.py --slot <fixture> -- <command...>` runs a command inside a heavy-fixture slot.
    import sys
    if sys.argv[1:] == ["--cpus"]:
        print(effective_cpus())
        sys.exit(0)
    if len(sys.argv) == 4 and sys.argv[1] == "--key":
        try:
            print(cache_key(sys.argv[2], sys.argv[3]))
            sys.exit(0)
        except CacheIdentityUnavailable as error:
            print(f"report cache identity unavailable: {error}", file=sys.stderr)
            sys.exit(2)
    if len(sys.argv) < 5 or sys.argv[1] != "--slot" or sys.argv[3] != "--":
        sys.exit("usage: report_cache.py --slot <fixture> -- <command...>")
    with heavy_slot(sys.argv[2]):
        sys.exit(subprocess.run(sys.argv[4:]).returncode)
