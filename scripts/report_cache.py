"""Shared `--json` runner for the Python tests: reads scripts/test.sh's prefetched reports and runs
the rest in parallel.

scripts/test.sh exports ELISA_PROOF_REPORT_CACHE when ELISA_PROOF_JOBS>1; its entries were made
by scripts/prefetch_reports.py with build/elisa-proof in this same run, so a cached entry is
reused only for that binary. Anything else runs the verifier as before.
"""
import concurrent.futures
import contextlib
import fcntl
import hashlib
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BINARY = ROOT / "build/elisa-proof"


# A fixture that includes the kernel sources (or is large) peaks at ~2.7 GB of memory; the
# runner shares a few slots for them across every process of one test run, so a 12-core box with
# 8 GB does not run out. ELISA_PROOF_HEAVY_JOBS overrides the slot count.
HEAVY_PEAK_KB = 2_800_000


def is_heavy(path) -> bool:
    try:
        if os.path.getsize(path) > 20_000:
            return True
        with open(path, encoding="utf-8") as source:
            return re.search(r'^include "\.\./src/', source.read(), re.MULTILINE) is not None
    except OSError:
        return False


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


def cache_key(path) -> str:
    return hashlib.sha1(os.path.realpath(str(path)).encode("utf-8")).hexdigest()


def _cached(binary, path):
    cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
    if not cache or os.path.realpath(str(binary)) != os.path.realpath(str(DEFAULT_BINARY)):
        return None
    entry = os.path.join(cache, cache_key(path))
    pending = os.path.join(cache, "pending", cache_key(path))
    # A prefetch that is still running this fixture finishes it sooner than a second run would.
    while os.path.exists(pending) and not os.path.exists(entry + ".rc"):
        time.sleep(0.5)  # poll-ok: local file from our own prefetcher
    if not os.path.exists(entry + ".rc"):
        return None
    with open(entry + ".json", encoding="utf-8") as out, open(entry + ".rc", encoding="utf-8") as rc:
        return int(rc.read().strip()), out.read()


def json_run(path, binary=DEFAULT_BINARY, timeout=600):
    """(returncode, stdout) of `binary --json path`, from the prefetch cache when it has it."""
    hit = _cached(binary, path)
    if hit is not None:
        return hit
    with heavy_slot(path):
        run = subprocess.run([str(binary), "--json", str(path)], capture_output=True, text=True, timeout=timeout)
    return run.returncode, run.stdout


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
    if len(sys.argv) < 5 or sys.argv[1] != "--slot" or sys.argv[3] != "--":
        sys.exit("usage: report_cache.py --slot <fixture> -- <command...>")
    with heavy_slot(sys.argv[2]):
        sys.exit(subprocess.run(sys.argv[4:]).returncode)
