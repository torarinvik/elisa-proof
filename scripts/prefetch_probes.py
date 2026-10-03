#!/usr/bin/env python3
"""Run every literal `run_probe` line of scripts/dogfood.sh in parallel, up front.

dogfood.sh stays a serial list of probes and assertions; this only moves the verifier runs ahead
of it. A probe runs the verifier twice (the second run is the determinism check), so each of the
two runs is its own work item and both stay independent processes. Run <n> of a probe is stored
as <cache>/<label>.<n>.json with its stderr in .err and its exit status in .rc, written last so
its presence marks a complete entry; <label>.pending marks a probe this prefetch will run. The
cache directory belongs to one dogfood run and one binary, so a stored run is exactly what the
serial call would have produced; a probe that is not listed here (or whose run failed to start)
runs serially as before.

Usage: prefetch_probes.py <dogfood.sh> <binary> <cache-dir> <root-dir> [jobs]
"""
import concurrent.futures
import glob
import os
import re
import signal
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_cache import effective_cpus, heavy_slot, heavy_slots  # noqa: E402

PROBE_LINE = re.compile(r"^run_probe ([A-Za-z0-9_]+) ([A-Za-z0-9_./-]+\.elisa) [0-9]+\s*$", re.MULTILINE)


def probes(dogfood_script: str, root: str) -> list[tuple[str, str]]:
    """(label, absolute source) of every literal probe, in the order dogfood.sh runs them."""
    parts = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(dogfood_script)), "dogfood.d", "*.sh")))
    found = []
    for path in parts:
        with open(path, encoding="utf-8") as part:
            found += [(label, os.path.join(root, source)) for label, source in PROBE_LINE.findall(part.read())]
    # A label named twice could hand one probe the other's stored run: leave those serial.
    labels = [label for label, _ in found]
    return [(label, path) for label, path in found if labels.count(label) == 1 and os.path.isfile(path)]


# Verifier runs in flight, so that a dogfood run that stops early stops them too.
RUNNING: set = set()
RUNNING_LOCK = threading.Lock()


def stop(_signum, _frame) -> None:
    with RUNNING_LOCK:
        for process in RUNNING:
            process.kill()
    os._exit(1)


def run_one(binary: str, cache: str, label: str, path: str, run: int) -> None:
    stem = os.path.join(cache, f"{label}.{run}")
    with open(stem + ".json.tmp", "wb") as out, open(stem + ".err.tmp", "wb") as err, heavy_slot(path, cache):
        with RUNNING_LOCK:
            process = subprocess.Popen([binary, "--json", path], stdout=out, stderr=err)
            RUNNING.add(process)
        status = process.wait()
        with RUNNING_LOCK:
            RUNNING.discard(process)
    os.replace(stem + ".json.tmp", stem + ".json")
    os.replace(stem + ".err.tmp", stem + ".err")
    with open(stem + ".rc.tmp", "w", encoding="utf-8") as rc:
        rc.write(f"{status}\n")
    os.replace(stem + ".rc.tmp", stem + ".rc")


def main() -> int:
    dogfood_script, binary, cache, root = sys.argv[1:5]
    signal.signal(signal.SIGTERM, stop)
    jobs = int(sys.argv[5]) if len(sys.argv) > 5 else effective_cpus()
    os.makedirs(cache, exist_ok=True)
    listed = probes(dogfood_script, root)
    # A pending marker tells run_probe to wait for this probe's runs instead of starting its own.
    for label, _ in listed:
        open(os.path.join(cache, f"{label}.pending"), "w").close()
    # Both runs of the biggest sources first: they dominate wall time. The serial gate reads the
    # probes in file order, so the rest follow in that order.
    big = set(sorted((path for _, path in listed), key=os.path.getsize, reverse=True)[:len(listed) // 8])
    ordered = [item for item in listed if item[1] in big] + [item for item in listed if item[1] not in big]
    work = [(label, path, run) for label, path in ordered for run in (1, 2)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda item: run_one(binary, cache, *item), work))
    print(f"prefetched {len(listed)} dogfood probes with {jobs} jobs ({heavy_slots()} heavy slots)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
