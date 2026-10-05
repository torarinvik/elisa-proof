#!/usr/bin/env python3
"""Run every literal `run_json_report` fixture and every `run_py_test` script of scripts/test.sh
in parallel, up front.

test.sh stays a serial list of assertions; this only moves the expensive verifier runs ahead of
it. Each report is stored as <cache>/<key>.json with its exit status in <key>.rc, keyed by the
fixture's absolute path. The cache directory belongs to one test run and one binary, so a stored
report is exactly what the serial call would have produced. A Python test's combined output is
stored as <cache>/py-<name>.out with its status in py-<name>.rc. Fixtures that are not prefetched (or
whose run failed to start) simply run serially as before.

Usage: prefetch_reports.py <test.sh> <binary> <cache-dir> <root-dir> [jobs]
ELISA_PROOF_SHARDS="a,b,.../N" runs only the work items whose index mod N is listed, so several
hosts with the same checkout path can split one run (scripts/remote/farm.sh).
"""
import concurrent.futures
import glob
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_cache import cache_key, effective_cpus, heavy_slot, heavy_slots  # noqa: E402


def matrix_text(test_script: str) -> str:
    """test.sh plus the ordered parts it sources from scripts/test.d."""
    parts = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(test_script)), "test.d", "*.sh")))
    return "".join(open(path, encoding="utf-8").read() for path in [test_script, *parts])


def fixtures(test_script: str, root: str) -> list[str]:
    text = matrix_text(test_script)
    found = set(re.findall(r'run_json_report "\$ROOT_DIR/([^"$]*\.elisa)"', text))
    # scripts/test_near_miss.py reads every rejected example through scripts/report_cache.py.
    found |= {os.path.join("examples", name) for name in os.listdir(os.path.join(root, "examples"))
              if name.startswith("rejected") and name.endswith(".elisa")}
    paths = [os.path.join(root, rel) for rel in found if os.path.isfile(os.path.join(root, rel))]
    # Biggest first: the kernel fixtures dominate wall time and should start immediately.
    return sorted(paths, key=os.path.getsize, reverse=True)


def py_tests(test_script: str, root: str) -> list[str]:
    text = matrix_text(test_script)
    names = re.findall(r'^\s*run_py_test (test_[a-z_0-9]+\.py)\s*$', text, re.MULTILINE)
    return [name for name in dict.fromkeys(names) if os.path.isfile(os.path.join(root, "scripts", name))]


def run_py(root: str, cache: str, name: str) -> None:
    out_path = os.path.join(cache, f"py-{name}.out")
    script = os.path.join(root, "scripts", name)
    # A test that runs the stage1 compiler peaks like a kernel fixture: give it a heavy slot.
    with open(script, encoding="utf-8") as source:
        compiles = re.search(r"elisac|stage1|SELF_HOST|compiler_provenance", source.read()) is not None
    with open(out_path + ".tmp", "wb") as out, heavy_slot(script, cache, force=compiles):
        status = subprocess.run(["python3", os.path.join(root, "scripts", name)], stdout=out,
                                stderr=subprocess.STDOUT, cwd=root).returncode
    os.replace(out_path + ".tmp", out_path)
    with open(os.path.join(cache, f"py-{name}.rc.tmp"), "w", encoding="utf-8") as rc:
        rc.write(f"{status}\n")
    os.replace(os.path.join(cache, f"py-{name}.rc.tmp"), os.path.join(cache, f"py-{name}.rc"))


def run_one(binary: str, cache: str, path: str) -> None:
    key = cache_key(path, binary)
    # Marks a fixture in progress so a reader waits for it instead of running it twice.
    pending = os.path.join(cache, "pending", key)
    out_path = os.path.join(cache, key + ".json")
    digest_path = os.path.join(cache, key + ".sha256")
    status_path = os.path.join(cache, key + ".rc")
    open(pending, "w").close()
    try:
        with open(out_path + ".tmp", "wb") as out, heavy_slot(path, cache):
            status = subprocess.run([binary, "--json", path], stdout=out, stderr=subprocess.DEVNULL).returncode
        payload_digest = hashlib.sha256(Path(out_path + ".tmp").read_bytes()).hexdigest()
        with open(digest_path + ".tmp", "w", encoding="ascii") as digest:
            digest.write(f"{payload_digest}\n")
        with open(status_path + ".tmp", "w", encoding="ascii") as rc:
            rc.write(f"{status}\n")
        # Publish the status last; a reader accepts the entry only when all three files agree.
        os.replace(out_path + ".tmp", out_path)
        os.replace(digest_path + ".tmp", digest_path)
        os.replace(status_path + ".tmp", status_path)
    finally:
        for temporary in (out_path + ".tmp", digest_path + ".tmp", status_path + ".tmp"):
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        try:
            os.unlink(pending)
        except FileNotFoundError:
            pass


def main() -> int:
    test_script, binary, cache, root = sys.argv[1:5]
    jobs = int(sys.argv[5]) if len(sys.argv) > 5 else effective_cpus()
    os.makedirs(os.path.join(cache, "pending"), exist_ok=True)
    paths = fixtures(test_script, root)
    scripts = py_tests(test_script, root)
    # Large fixtures first, then the Python tests, then the many small fixtures.
    big, small = paths[:len(paths) // 8], paths[len(paths) // 8:]
    # ELISA_PROOF_PREFETCH_PHASE=fixtures|tests runs one half (scripts/remote/farm.sh runs the
    # Python tests only after every host's fixtures are gathered, so they never re-run one).
    phase = os.environ.get("ELISA_PROOF_PREFETCH_PHASE", "all")
    work = []
    if phase in ("all", "fixtures"):
        work += [lambda p=p: run_one(binary, cache, p) for p in big]
    if phase in ("all", "tests"):
        work += [lambda n=n: run_py(root, cache, n) for n in scripts]
    if phase in ("all", "fixtures"):
        work += [lambda p=p: run_one(binary, cache, p) for p in small]
    shards = os.environ.get("ELISA_PROOF_SHARDS")
    if shards:
        mine, total = shards.split("/")
        keep = {int(index) for index in mine.split(",") if index}
        work = [job for index, job in enumerate(work) if index % int(total) in keep]
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda job: job(), work))
    print(f"prefetched {len(paths)} reports and {len(scripts)} tests with {jobs} jobs "
          f"({heavy_slots()} heavy slots)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
